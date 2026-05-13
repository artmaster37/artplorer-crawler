import requests
import json
import os
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

def init_firebase():
    firebase_key = os.environ.get('FIREBASE_KEY')
    key_dict = json.loads(firebase_key)
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred, {
        'projectId': key_dict['project_id'],
    })
    return firestore.client()

def fetch_seoul_exhibitions(seoul_key):
    all_items = []
    base_url = f"https://openapi.seoul.go.kr:443/rest/{seoul_key}/json/culturalEventInfo"

    for start in range(1, 1001, 200):
        end = start + 199
        url = f"{base_url}/{start}/{end}/"

        # 3번 재시도
        for attempt in range(3):
            try:
                print(f"📡 서울시 {start}~{end} 요청 중... (시도 {attempt+1})")
                res = requests.get(url, timeout=60)
                data = res.json()

                result_code = data.get('culturalEventInfo', {}).get('RESULT', {}).get('CODE', '')
                if result_code == 'INFO-200':
                    print("📭 데이터 없음 - 종료")
                    return all_items

                rows = data.get('culturalEventInfo', {}).get('row', [])
                if not rows:
                    return all_items

                for i, row in enumerate(rows):
                    codename = row.get('CODENAME', '')
                    if '전시' not in codename:
                        continue

                    lat = float(row.get('LAT') or 0)
                    lon = float(row.get('LOT') or 0)
                    if lat == 0: lat = 37.5665
                    if lon == 0: lon = 126.9780

                    all_items.append({
                        'id': f"seoul_{start + i}",
                        'title': row.get('TITLE', '제목 없음'),
                        'artist': row.get('PLAYER', '정보 없음'),
                        'venue': row.get('PLACE', '장소 미정'),
                        'address': row.get('PLACE', ''),
                        'startDate': row.get('STRTDATE', ''),
                        'endDate': row.get('END_DATE', ''),
                        'latitude': lat,
                        'longitude': lon,
                        'imageUrls': [row['MAIN_IMG']] if row.get('MAIN_IMG') else [],
                        'description': row.get('PROGRAM', '상세 정보가 없습니다.'),
                        'source': 'seoul',
                        'updatedAt': datetime.now().isoformat(),
                    })

                print(f"✅ {len(rows)}개 수신 완료")
                break  # 성공하면 재시도 중단

            except Exception as e:
                print(f"⚠️ 시도 {attempt+1} 실패: {e}")
                if attempt < 2:
                    print("5초 후 재시도...")
                    time.sleep(5)
                else:
                    print(f"❌ {start}~{end} 최종 실패, 다음으로 넘어감")

        time.sleep(2)  # 요청 간 딜레이

    return all_items

def save_to_firebase(db, exhibitions):
    if not exhibitions:
        print("⚠️ 저장할 데이터 없음")
        return

    collection = db.collection('exhibitions')
    batch = db.batch()
    count = 0

    for ex in exhibitions:
        doc_ref = collection.document(ex['id'])
        batch.set(doc_ref, ex)
        count += 1

        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
            print(f"💾 {count}개 저장 완료...")

    batch.commit()
    print(f"🎉 총 {count}개 저장 완료!")

def main():
    seoul_key = os.environ.get('SEOUL_API_KEY')
    print("🚀 데이터 수집 시작...")

    db = init_firebase()
    print("✅ Firebase 연결 성공!")

    exhibitions = fetch_seoul_exhibitions(seoul_key)
    print(f"📊 수집된 전시: {len(exhibitions)}개")

    save_to_firebase(db, exhibitions)
    print("✅ 완료!")

if __name__ == "__main__":
    main()
