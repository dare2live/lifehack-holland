import json
import duckdb
from pathlib import Path

DB_PATH = Path("backend/data/holland.duckdb")

def import_raw_materials():
    print("Connecting to DuckDB...")
    con = duckdb.connect(str(DB_PATH))
    
    # ═══════════════════════════════════════════════════════════════════
    # 1. Import MBTI IPIP 88 Items
    # ═══════════════════════════════════════════════════════════════════
    print("Importing MBTI 88 items...")
    con.execute("DROP TABLE IF EXISTS raw_mbti_ipip")
    con.execute("""
        CREATE TABLE raw_mbti_ipip (
            item_id VARCHAR PRIMARY KEY,
            question_text VARCHAR,
            option_a VARCHAR,
            option_b VARCHAR
        )
    """)
    
    mbti_file = Path("backend/data/ipip/mbti_88_items.json")
    if mbti_file.exists():
        with open(mbti_file, "r", encoding="utf-8") as f:
            mbti_data = json.load(f)
        
        for idx, item in enumerate(mbti_data["questions"]):
            item_id = f"MBTI_88_{idx+1}"
            text = item["title"]
            opt_a = item["selections"][0]
            opt_b = item["selections"][1]
            con.execute(
                "INSERT INTO raw_mbti_ipip VALUES (?, ?, ?, ?)",
                (item_id, text, opt_a, opt_b)
            )
        print(f"✅ Successfully inserted 88 MBTI items into 'raw_mbti_ipip'.")
    else:
        print(f"❌ Could not find {mbti_file}")


    # ═══════════════════════════════════════════════════════════════════
    # 2. Import O*NET Tasks and Map to Holland RIASEC
    # ═══════════════════════════════════════════════════════════════════
    print("Importing O*NET Tasks and Interests...")
    con.execute("DROP TABLE IF EXISTS raw_onet_tasks")
    con.execute("""
        CREATE TABLE raw_onet_tasks (
            task_id VARCHAR PRIMARY KEY,
            soc_code VARCHAR,
            task_statement VARCHAR,
            primary_riasec VARCHAR
        )
    """)
    
    soc_to_riasec = {}
    from backend.config import RIASEC_MAP
    
    interests_file = Path("backend/data/onet/Interests.txt")
    if interests_file.exists():
        with open(interests_file, "r", encoding="utf-8") as f:
            headers = f.readline()
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 5:
                    soc_code = parts[0]
                    element_id = parts[1]
                    data_value = parts[4]
                    
                    # 1.B.1.g is 'First Interest High-Point'
                    if element_id == "1.B.1.g": 
                        if data_value in RIASEC_MAP:
                            soc_to_riasec[soc_code] = RIASEC_MAP[data_value]
    
    tasks_file = Path("backend/data/onet/Task_Statements.txt")
    tasks_inserted = 0
    if tasks_file.exists():
        with open(tasks_file, "r", encoding="utf-8") as f:
            headers = f.readline()
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 3:
                    soc_code = parts[0]
                    task_id = parts[1]
                    task_statement = parts[2]
                    
                    # Map to RIASEC based on SOC code's First Interest High-Point
                    primary_riasec = soc_to_riasec.get(soc_code, "Unknown")
                    
                    con.execute(
                        "INSERT INTO raw_onet_tasks VALUES (?, ?, ?, ?)",
                        (task_id, soc_code, task_statement, primary_riasec)
                    )
                    tasks_inserted += 1
        print(f"✅ Successfully inserted {tasks_inserted} O*NET tasks into 'raw_onet_tasks'.")
    else:
        print(f"❌ Could not find {tasks_file}")
    
    con.close()

if __name__ == "__main__":
    import_raw_materials()
