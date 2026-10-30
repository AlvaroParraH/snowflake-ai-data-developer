import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PythonBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="snowflake-bootstrap-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        self.installer = self.directory / "install.sh"
        self.atomic_marker = self.directory / "ostree-booted"
        self.installer.write_text((ROOT / "install.sh").read_text().replace(
            "/run/ostree-booted", str(self.atomic_marker),
        ))
        dirname = shutil.which("dirname")
        assert dirname is not None
        (self.bin / "dirname").symlink_to(dirname)
        self.environment = {
            **os.environ, "PATH": str(self.bin), "PYTHON": "",
            "BOOTSTRAP_LOG": str(self.directory / "commands"),
            "BOOTSTRAP_BIN": str(self.bin),
        }
        self.script("uname", "printf '%s\\n' Darwin\n")
        self.python_fixture = self.directory / "python fixture"
        self.python_fixture.write_text(
            "#!/bin/bash\n"
            "if [[ \"$1\" == '-c' ]]; then exit 0; fi\n"
            "printf '%s\\n' \"$0\" \"$@\" >> \"$BOOTSTRAP_LOG\"\n"
        )
        self.python_fixture.chmod(0o755)
        self.environment["PYTHON_FIXTURE"] = str(self.python_fixture)

    def script(self, name: str, body: str) -> Path:
        path = self.bin / name
        path.write_text("#!/bin/bash\n" + body)
        path.chmod(0o755)
        return path

    def package_manager(self, name: str, *, succeeds: bool = True,
                        provides_python: bool = True) -> None:
        body = 'printf "package %s\\n" "$*" >> "$BOOTSTRAP_LOG"\n'
        if not succeeds:
            body += "exit 1\n"
        elif provides_python:
            body += '/bin/cp "$PYTHON_FIXTURE" "$BOOTSTRAP_BIN/python3.11"\n'
        self.script(name, body)

    def run_installer(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/bash", str(self.installer), *args],
            env=self.environment, stdin=subprocess.DEVNULL, capture_output=True, text=True,
        )

    def log(self) -> str:
        path = Path(self.environment["BOOTSTRAP_LOG"])
        return path.read_text() if path.exists() else ""

    def test_existing_versioned_python_wins_over_old_python3(self) -> None:
        self.script("python3", "exit 1\n")
        shutil.copy2(self.python_fixture, self.bin / "python3.12")
        self.package_manager("brew")
        result = self.run_installer("--shared", "--dry-run", "--no-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("python3.12\n", self.log())
        self.assertIn("scripts/install_shared.py\n--dry-run\n--no-install\n", self.log())
        self.assertNotIn("package", self.log())

    def test_python_override_supports_spaces_and_project_dispatch(self) -> None:
        self.environment["PYTHON"] = str(self.python_fixture)
        result = self.run_installer("--target", "/project with spaces", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("scripts/install_kit.py\n--target\n/project with spaces\n", self.log())

    def test_yes_installs_python_on_macos_and_rechecks_version(self) -> None:
        self.script("python3", "exit 1\n")
        self.package_manager("brew")
        result = self.run_installer("--shared", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("package install python@3.11\n", self.log())
        self.assertIn("python3.11\n", self.log())
        self.assertIn("scripts/install_shared.py\n--yes\n", self.log())

    def test_default_flags_allow_bootstrap_and_are_forwarded(self) -> None:
        self.package_manager("brew")
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("scripts/install_shared.py\n--yes\n--personal-skills\n", self.log())

    def test_noninteractive_requires_yes_without_installing(self) -> None:
        self.package_manager("brew")
        result = self.run_installer("--shared")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires confirmation or --yes", result.stderr)
        self.assertEqual(self.log(), "")

    def test_protective_flags_never_install_even_with_yes(self) -> None:
        self.package_manager("brew")
        for flag in ("--no-install", "--dry-run", "--help", "-h", "--update"):
            with self.subTest(flag=flag):
                result = self.run_installer("--shared", "--yes", flag)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("installation is disabled", result.stderr)
                self.assertEqual(self.log(), "")

    @unittest.skipUnless(hasattr(os, "openpty"), "Requires a POSIX terminal")
    def test_interactive_confirmation_accepts_or_declines_installation(self) -> None:
        self.package_manager("brew")
        for reply, accepted in ((b"n\n", False), (b"yes\n", True)):
            with self.subTest(accepted=accepted):
                master, slave = os.openpty()
                try:
                    os.write(master, reply)
                    result = subprocess.run(
                        ["/bin/bash", str(self.installer), "--shared"],
                        env=self.environment, stdin=slave, capture_output=True,
                        text=True, timeout=15,
                    )
                finally:
                    os.close(master)
                    os.close(slave)
                if accepted:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("package install python@3.11", self.log())
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("installation declined", result.stderr)
                    self.assertEqual(self.log(), "")

    def test_unsupported_system_or_missing_package_manager_requires_manual_install(self) -> None:
        for system in ("Darwin", "Linux", "Windows_NT"):
            with self.subTest(system=system):
                self.script("uname", f"printf '%s\\n' {system}\n")
                result = self.run_installer("--shared", "--yes")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Install it manually", result.stderr)
                self.assertEqual(self.log(), "")

    def test_package_manager_failure_does_not_launch_python(self) -> None:
        self.package_manager("brew", succeeds=False)
        result = self.run_installer("--shared", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Python installation failed", result.stderr)
        self.assertNotIn("scripts/install_shared.py", self.log())

    def test_success_without_usable_python_does_not_continue(self) -> None:
        self.package_manager("brew", provides_python=False)
        result = self.run_installer("--shared", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Python 3.10+ is not on PATH", result.stderr)
        self.assertNotIn("scripts/install_shared.py", self.log())

    def test_supported_linux_package_managers(self) -> None:
        self.script("uname", "printf '%s\\n' Linux\n")
        self.script("sudo", 'exec "$@"\n')
        for manager, arguments in (
            ("apt-get", "install -y python3 python3-venv python3-pip"),
            ("dnf", "install -y python3 python3-pip"),
            ("pacman", "-S --noconfirm python python-pip"),
        ):
            with self.subTest(manager=manager):
                self.package_manager(manager)
                result = self.run_installer("--shared", "--yes")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"package {arguments}\n", self.log())
                (self.bin / manager).unlink()
                (self.bin / "python3.11").unlink()
                Path(self.environment["BOOTSTRAP_LOG"]).unlink()

    def test_atomic_host_never_installs_or_reboots(self) -> None:
        self.script("uname", "printf '%s\\n' Linux\n")
        self.atomic_marker.touch()
        for manager in ("apt-get", "dnf", "pacman", "rpm-ostree", "systemctl"):
            self.package_manager(manager)
        for args in ((), ("--shared", "--yes"), ("--shared",),
                     ("--shared", "--yes", "--dry-run"),
                     ("--shared", "--yes", "--no-install")):
            with self.subTest(args=args):
                result = self.run_installer(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Fedora Atomic/OSTree host", result.stdout)
                self.assertIn("sudo rpm-ostree install python3 python3-pip", result.stdout)
                self.assertIn("systemctl reboot", result.stdout)
                self.assertNotIn("distrobox enter", result.stdout)
                self.assertEqual(self.log(), "")

    def test_atomic_host_offers_existing_distrobox_without_running_it(self) -> None:
        self.script("uname", "printf '%s\\n' Linux\n")
        self.atomic_marker.touch()
        self.package_manager("distrobox")
        result = self.run_installer("--shared", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("distrobox enter <your-box> -- sudo dnf install", result.stdout)
        self.assertIn("inside that box, not on the host", result.stdout)
        self.assertEqual(self.log(), "")

    def test_atomic_host_with_usable_python_continues_without_installation(self) -> None:
        self.script("uname", "printf '%s\\n' Linux\n")
        self.atomic_marker.touch()
        shutil.copy2(self.python_fixture, self.bin / "python3.12")
        self.package_manager("rpm-ostree")
        result = self.run_installer("--shared", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("scripts/install_shared.py", self.log())
        self.assertNotIn("package", self.log())


if __name__ == "__main__":
    unittest.main()
