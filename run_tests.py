#!/usr/bin/env python3
import subprocess
import sys


def run_tests():
    print("🚀 Запуск тестов Travel Planner...")

    commands = [
        [sys.executable, "-m", "pytest", "unittests.py",
         "--html=report.html", "--self-contained-html", "-v"],

        [sys.executable, "-m", "pytest", "unittests.py",
         "--junit-xml=junit-report.xml"],
    ]

    for cmd in commands:
        print(f"\n📊 Выполняется: {' '.join(cmd)}")
        result = subprocess.run(cmd)

        if result.returncode == 0:
            print("✅ Тесты прошли успешно!")
        else:
            print("❌ Некоторые тесты не прошли")
            return result.returncode

    print("\n📈 Отчеты сгенерированы:")
    print("   - HTML отчет: report.html")
    print("   - JUnit отчет: junit-report.xml")

    return 0


if __name__ == "__main__":
    sys.exit(run_tests())