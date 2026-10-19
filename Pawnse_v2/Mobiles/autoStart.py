import os
import sys
import winreg

# นำเข้า PawseApp จาก main.py (กรณีไฟล์ autoStart.py อยู่ไดเรกทอรีเดียวกัน)
from main import PawseApp


def set_autostart(enabled=True):
    app_name = "Pawse"

    # หาตำแหน่ง Absolute Path ของ main.py อิงจากโฟลเดอร์ปัจจุบัน
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_path = os.path.join(base_dir, "main.py")

    # คำสั่งรันผ่าน Python executable พร้อมแนบแฟล็ก --silent
    app_path = f'"{sys.executable}" "{main_path}" --silent'

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS
        )
        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
        else:
            winreg.DeleteValue(key, app_name)
        winreg.CloseKey(key)
        print(f"[Pawse] Autostart set to {enabled}")
    except Exception as e:
        print(f"Failed to update registry: {e}")


if __name__ == "__main__":
    # บันทึกค่าเปิดใช้งาน Autostart ลง Registry
    set_autostart(True)

    # สร้าง Instance และเริ่มการทำงานของแอป
    pawse = PawseApp()

    # หากรันจากการ Boot เครื่อง (มีแฟล็ก --silent) ให้ซ่อนหน้าต่างหลักไว้
    # หากรันจากการ Boot เครื่อง (มีแฟล็ก --silent) ให้ซ่อนหน้าต่างหลักไว้
    if "--silent" not in sys.argv:
        pawse.show_tasks()  # 👈 เปลี่ยนจาก show_main_window() เป็น show_tasks()

    sys.exit(pawse.run())