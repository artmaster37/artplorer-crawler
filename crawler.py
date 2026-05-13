import requests
import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase 초기화
def init_firebase():
    firebase_key = os.environ.get('FIREBASE_KEY')
    key_dict = json.loads(firebase_key)
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred, {
        'projectId': key_dict['project_id'],
    })
    return firestore.client()

# 서울시 전시 데이터 수집
def fetch_seoul_exhibitions(seoul_key):
    all_items = []
    base_url = f"https://openapi.seoul.go.kr:443/rest/{seoul_key}/json/culturalEventInfo"

    for start in range(1, 1001, 200):
        end = start + 199
        url = f"{base_url}/{start}/{end}/"
        try:
            res = requests.get(url, timeout=30)
            data = res.json()
            rows = data.get('culturalEventInfo', {}).get('row', [])
            if not rows:
                break
            for i, row in enumerate(rows):
                codename = row.get('CODENAME', '')
                if '전시' not in codename:
                    continue
                lat = float(row.get('LAT') or 0)
                lon = float(row.get('LOT') or 0)
                if lat == 0:
                    lat = 37.5665
                if lon == 0:
                    lon = 126.9780
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
            print(f"✅ 서울시 {start}~{end}: {len(rows)}개 수신")
        except Exception as e:
            print(f"❌ 서울시 오류 ({start}~{end}): {e}")
            break

    return all_items

# Firebase에 저장
def save_to_firebase(db, exhibitions):
    collection = db.collection('exhibitions')
    batch = db.batch()
    count = 0

    for ex in exhibitions:
        doc_ref = collection.document(ex['id'])
        batch.set(doc_ref, ex)
        count += 1

        # Firestore 배치는 500개 제한
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
    exhibitions = fetch_seoul_exhibitions(seoul_key)

    print(f"📊 수집된 전시: {len(exhibitions)}개")
    save_to_firebase(db, exhibitions)
    print("✅ 완료!")

if __name__ == "__main__":
    main()
