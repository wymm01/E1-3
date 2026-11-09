import json   # JSON 파일을 읽는 도구
import time   # 시간 재기 도구

# 점수 비교 기준: 차이가 이 값보다 작으면 "같다"고 본다 (epsilon)
EPSILON = 1e-9

# 성능 분석의 3x3 기준 데이터 (십자가 필터와 십자가 패턴)
SAMPLE_FILTER_3 = [
    [0, 1, 0],
    [1, 1, 1],
    [0, 1, 0],
]
SAMPLE_PATTERN_3 = [
    [0, 1, 0],
    [1, 1, 1],
    [0, 1, 0],
]


# MAC 연산: 패턴과 필터를 같은 위치끼리 곱해서 모두 더한다
def mac(pattern, filt):
    total = 0
    n = len(pattern)
    for i in range(n):
        for j in range(n):
            total += pattern[i][j] * filt[i][j]
    return total


# MAC 연산을 repeat번 반복해서 평균 시간(ms)을 구한다
def measure_ms(pattern, filt, repeat=10):
    start = time.perf_counter()
    for _ in range(repeat):
        mac(pattern, filt)
    end = time.perf_counter()
    return (end - start) / repeat * 1000


# 성능 표 출력: rows는 (크기 N, 평균 시간 ms) 목록
def print_perf_table(rows):
    print("\n===== 성능 분석 (MAC 연산 10회 반복 평균) =====")
    print("크기(NxN) | 평균 시간(ms) | 연산 횟수(N²)")
    print("-" * 42)
    for n, ms in rows:
        print(f"{n:>3}x{n:<3}   | {ms:>13.6f} | {n * n:>13}")


# 두 점수를 비교해서 판정하기 (모드 1: A / B / 판정 불가)
def judge(score_a, score_b):
    if abs(score_a - score_b) < EPSILON:
        return "판정 불가"
    elif score_a > score_b:
        return "A"
    else:
        return "B"


# 한 줄 입력받기: 숫자 size개를 공백으로 구분해서 입력해야 통과
def read_row(prompt, size):
    while True:
        line = input(prompt)
        parts = line.split()

        if len(parts) != size:
            print(f"입력 형식 오류: 각 줄에 {size}개의 숫자를 공백으로 구분해 입력하세요.")
            continue

        try:
            numbers = [float(p) for p in parts]
        except ValueError:
            print(f"입력 형식 오류: 숫자만 입력할 수 있습니다. 각 줄에 {size}개의 숫자를 공백으로 구분해 입력하세요.")
            continue

        return numbers


# 표 전체(size줄) 입력받기
def read_matrix(title, size=3):
    print(f"\n[{title}] {size}줄을 입력하세요. (한 줄에 숫자 {size}개, 공백으로 구분)")
    matrix = []
    for r in range(size):
        row = read_row(f"{r + 1}번째 줄: ", size)
        matrix.append(row)
    return matrix


# 입력된 표를 보기 좋게 출력하기
def show_matrix(title, matrix):
    print(f"\n{title} 저장 완료:")
    for row in matrix:
        print("  ", row)


# 모드 1: 사용자 입력 모드
def run_mode1():
    filter_a = read_matrix("필터 A")
    show_matrix("필터 A", filter_a)

    filter_b = read_matrix("필터 B")
    show_matrix("필터 B", filter_b)

    pattern = read_matrix("패턴")
    show_matrix("패턴", pattern)

    score_a = mac(pattern, filter_a)
    score_b = mac(pattern, filter_b)
    time_ms = measure_ms(pattern, filter_a, repeat=10)

    print("\n===== 결과 =====")
    print("필터 A 점수:", score_a)
    print("필터 B 점수:", score_b)
    print(f"연산 시간(평균 10회): {time_ms:.6f} ms")
    print("판정:", judge(score_a, score_b))

    print_perf_table([(3, time_ms)])


# ---------------- 여기부터 모드 2(data.json)용 코드 ----------------

# data.json 파일 읽어오기 (실패해도 프로그램이 꺼지지 않게 처리)
def load_data(path="data.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {path} (main.py와 같은 폴더에 넣어주세요)")
    except json.JSONDecodeError:
        print(f"{path} 파일의 형식이 올바른 JSON이 아닙니다.")
    return None


# 라벨 정규화: 여러 가지로 적힌 이름을 표준 라벨(Cross, X) 두 가지로 통일한다
#   '+' 또는 'cross' -> "Cross"
#   'x'              -> "X"
#   그 외            -> None (알 수 없는 라벨)
def normalize_label(raw):
    if not isinstance(raw, str):        # 글자가 아니면 알 수 없는 라벨
        return None
    text = raw.strip().lower()          # 앞뒤 공백 제거 + 소문자로 통일
    if text == "+" or text == "cross":
        return "Cross"
    if text == "x":
        return "X"
    return None


# 키 이름에서 크기 N 꺼내기: "size_13_2" -> 13, "size_5" -> 5
def extract_size(key):
    parts = key.split("_")              # "size_13_2" -> ["size", "13", "2"]
    if len(parts) >= 2 and parts[0] == "size" and parts[1].isdigit():
        return int(parts[1])
    return None


# 표가 정확히 n x n 크기인지 검사
def is_size_n(matrix, n):
    if not isinstance(matrix, list) or len(matrix) != n:
        return False
    for row in matrix:
        if not isinstance(row, list) or len(row) != n:
            return False
    return True


# 필터들을 크기별로 정리하기
# 결과 모양: {5: {"Cross": 표, "X": 표}, 13: {...}, 25: {...}}
def build_filters(data):
    result = {}
    for size_key, group in data.get("filters", {}).items():
        n = extract_size(size_key)
        if n is None or not isinstance(group, dict):
            print(f"[경고] 필터 키 '{size_key}'를 이해할 수 없어 건너뜁니다.")
            continue
        result[n] = {}
        for raw_label, matrix in group.items():
            label = normalize_label(raw_label)      # 'cross' -> "Cross", 'x' -> "X"
            if label is None:
                print(f"[경고] {size_key}의 필터 이름 '{raw_label}'을(를) 이해할 수 없어 건너뜁니다.")
                continue
            result[n][label] = matrix
    return result


# 케이스 1개를 판정한다. 문제가 있어도 프로그램이 꺼지지 않고 FAIL로 기록만 한다.
def evaluate_case(key, case, filters_by_size):
    result = {
        "key": key,
        "cross": None,
        "x": None,
        "verdict": None,
        "expected": None,
        "status": "FAIL",
        "reason": "",
    }

    n = extract_size(key)
    if n is None:
        result["reason"] = "키 형식 오류: size_N_번호 형태가 아닙니다"
        return result

    if not isinstance(case, dict) or "input" not in case or "expected" not in case:
        result["reason"] = "스키마 오류: input 또는 expected 항목이 없습니다"
        return result

    expected = normalize_label(case["expected"])
    if expected is None:
        result["reason"] = f"라벨 오류: 알 수 없는 expected 값 ({case['expected']})"
        return result
    result["expected"] = expected

    group = filters_by_size.get(n)
    if group is None or "Cross" not in group or "X" not in group:
        result["reason"] = f"필터 없음: size_{n}의 Cross/X 필터를 찾을 수 없습니다"
        return result

    pattern = case["input"]
    cross_filter = group["Cross"]
    x_filter = group["X"]

    if not is_size_n(pattern, n):
        result["reason"] = f"크기 불일치: 패턴이 {n}x{n} 크기가 아닙니다"
        return result
    if not is_size_n(cross_filter, n) or not is_size_n(x_filter, n):
        result["reason"] = f"크기 불일치: size_{n} 필터가 {n}x{n} 크기가 아닙니다"
        return result

    try:
        cross_score = mac(pattern, cross_filter)
        x_score = mac(pattern, x_filter)
    except TypeError:
        result["reason"] = "연산 오류: 표 안에 숫자가 아닌 값이 있습니다"
        return result

    result["cross"] = cross_score
    result["x"] = x_score

    # 판정: 차이가 epsilon보다 작으면 UNDECIDED(판정 불가)
    if abs(cross_score - x_score) < EPSILON:
        verdict = "UNDECIDED"
    elif cross_score > x_score:
        verdict = "Cross"
    else:
        verdict = "X"
    result["verdict"] = verdict

    if verdict == expected:
        result["status"] = "PASS"
    else:
        result["reason"] = f"판정({verdict})과 expected({expected})가 다릅니다"
    return result


# 크기별로 MAC 연산 시간을 재서 (크기, 평균 ms) 목록으로 돌려준다
def collect_perf_rows(patterns, filters_by_size):
    rows = []
    rows.append((3, measure_ms(SAMPLE_PATTERN_3, SAMPLE_FILTER_3, repeat=10)))   # 3x3 기준 데이터

    for n in sorted(filters_by_size):
        cross_filter = filters_by_size[n].get("Cross")
        if not is_size_n(cross_filter, n):
            continue

        # 같은 크기(n)의 패턴을 하나 찾는다
        sample = None
        for key, case in patterns.items():
            if extract_size(key) == n and isinstance(case, dict) and is_size_n(case.get("input"), n):
                sample = case["input"]
                break
        if sample is None:
            continue

        try:
            rows.append((n, measure_ms(sample, cross_filter, repeat=10)))
        except TypeError:
            continue     # 숫자가 아닌 값이 있으면 이 크기는 건너뛴다
    return rows


# 케이스 1개의 결과를 화면에 출력
def print_case(r):
    print(f"\n--- {r['key']} ---")
    if r["cross"] is not None:
        print(f"Cross 점수: {r['cross']:.4f}")
        print(f"X 점수: {r['x']:.4f}")
        print(f"판정: {r['verdict']} | expected: {r['expected']} | {r['status']}")
    else:
        print(f"{r['status']} (사유: {r['reason']})")


# 모드 2: data.json 분석
def run_mode2():
    data = load_data()
    if data is None:
        return

    filters_by_size = build_filters(data)
    patterns = data.get("patterns", {})

    print("\n===== data.json 분석 시작 =====")
    results = []
    for key, case in patterns.items():
        r = evaluate_case(key, case, filters_by_size)
        results.append(r)
        print_case(r)

    # 성능 분석 (3x3 포함, 5x5 / 13x13 / 25x25)
    print_perf_table(collect_perf_rows(patterns, filters_by_size))

    # 결과 요약
    total = len(results)
    passed = 0
    for r in results:
        if r["status"] == "PASS":
            passed += 1
    failed = total - passed

    print("\n===== 결과 요약 =====")
    print(f"전체 테스트 수: {total}")
    print(f"통과: {passed}")
    print(f"실패: {failed}")
    if failed > 0:
        print("실패 케이스 목록:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  - {r['key']}: {r['reason']}")


# 프로그램 시작: 모드 선택
def main():
    print("===== Mini NPU 시뮬레이터 =====")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")
    while True:
        choice = input("모드를 선택하세요 (1 또는 2): ").strip()
        if choice == "1":
            run_mode1()
            break
        elif choice == "2":
            run_mode2()
            break
        else:
            print("입력 오류: 1 또는 2를 입력하세요.")


main()