import os
import sqlite3
import sqlite3

def verify_images():
    print("=== Phase 1 Verification ===")
    
    # 1. Check generated PNGs
    media_dir = os.path.join("media", "cases")
    if not os.path.exists(media_dir):
        print("[FAIL] Media directory does not exist.")
        return
        
    pngs = [f for f in os.listdir(media_dir) if f.endswith(".png")]
    if len(pngs) < 6:
        print(f"[FAIL] Expected at least 6 PNGs, found {len(pngs)}.")
        return
    print(f"[PASS] Found {len(pngs)} PNGs in backend/media/cases/")
    
    # 2. Check Database Update
    conn = sqlite3.connect("bhoomidrishti.db")
    c = conn.cursor()
    c.execute("SELECT before_image_url, after_image_url FROM change_records LIMIT 5")
    rows = c.fetchall()
    
    has_placehold = False
    has_media = False
    for r in rows:
        if "placehold.co" in r[0] or "placehold.co" in r[1]:
            has_placehold = True
        if "/media/cases/" in r[0] and "/media/cases/" in r[1]:
            has_media = True
            
    if has_placehold:
        print("[FAIL] Database still contains placehold.co URLs!")
    elif has_media:
        print(f"[PASS] Database successfully updated to use /media/cases/ URLs. Example: {rows[0][0]}")
    else:
        print("[WARN] No media URLs found. Is the DB seeded?")
    
    conn.close()

if __name__ == "__main__":
    verify_images()
