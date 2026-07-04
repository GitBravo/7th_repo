"""
병무청 보도자료(hwpx) 구조 인식(structure-aware) 청킹 로직.
chunk_documents.py(배치 실행)와 watch_documents.py(실시간 감지) 양쪽에서 공유한다.

청킹 전략 (PLAN.md 참고):
- 번호("1.", "2." ...) 또는 네모("□") 헤더 단위로 섹션을 나눠 하나의 정책 항목 = 하나의 청크로 구성
- 헤더가 나오기 전의 리드 문단(제목/부제/요약)은 별도 청크로 분리
- 섹션이 800자를 넘으면 문장 경계 기준으로 추가 분할 (오버랩 약 80자)
- 모든 문서 끝에 반복되는 "담당 부서/담당자/연락처" 표는 보일러플레이트로 판단해 제거
- 임베딩 시에는 각 청크 앞에 "[문서 제목] (보도일자)"를 프리픽스로 붙여 문맥 손실 방지
  (embed_text 필드. content 필드는 프리픽스 없는 원문 그대로 보관)
"""

import html
import os
import re
import zipfile

MAX_CHUNK_LEN = 800
OVERLAP_LEN = 80

HEADER_PATTERN = re.compile(r"^(\d{1,2}\.\s+\S|□\s*\S)")
BOILERPLATE_PATTERN = re.compile(r"^담당\s*부서")
DATE_PATTERN = re.compile(r"\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.")
NOISE_EXACT = {"병무청", "보도자료", "보도시점", "배포", "배포이후"}
HANGUL_PATTERN = re.compile(r"[가-힣]")


def is_noise(paragraph):
    """제목/본문과 무관한 서식용 라벨(발행처, 날짜 등)을 걸러낸다."""
    if paragraph in NOISE_EXACT:
        return True
    if "엠바고" in paragraph:
        return True
    if not HANGUL_PATTERN.search(paragraph):
        return True
    return False


def extract_paragraphs(path):
    z = zipfile.ZipFile(path)
    section_files = sorted(n for n in z.namelist() if re.match(r"Contents/section\d+\.xml", n))
    paragraphs = []
    for sf in section_files:
        xml = z.read(sf).decode("utf-8")
        for p in re.findall(r"<hp:p[ >].*?</hp:p>", xml, re.DOTALL):
            runs = re.findall(r"<hp:t[^>]*>(.*?)</hp:t>", p, re.DOTALL)
            line = "".join(html.unescape(re.sub(r"<[^>]+>", "", r)) for r in runs).strip()
            if line:
                paragraphs.append(line)
    return paragraphs


def derive_title(filename):
    stem = filename.replace(".hwpx", "")
    stem = re.sub(r"^\d{8}", "", stem)
    stem = re.sub(r"\([^)]*\)", "", stem)
    return stem.strip(" ,")


def derive_press_date(paragraphs):
    for p in paragraphs:
        m = DATE_PATTERN.search(p)
        if m:
            return m.group(0).rstrip(".")
    return None


def strip_boilerplate(paragraphs):
    for i, p in enumerate(paragraphs):
        if BOILERPLATE_PATTERN.match(p):
            return paragraphs[:i]
    return paragraphs


def split_long_text(text, max_len=MAX_CHUNK_LEN, overlap=OVERLAP_LEN):
    if len(text) <= max_len:
        return [text]
    sentences = re.split(r"(?<=[.!?다])\s+", text)
    parts = []
    current = ""
    for sent in sentences:
        if current and len(current) + len(sent) + 1 > max_len:
            parts.append(current.strip())
            current = current[-overlap:] + " " + sent
        else:
            current = (current + " " + sent).strip()
    if current.strip():
        parts.append(current.strip())
    return parts


def split_into_sections(paragraphs):
    """헤더 이전 리드 문단을 첫 섹션으로, 이후 헤더 단위로 섹션 분리."""
    sections = []
    current_heading = "리드 문단"
    current_lines = []
    for p in paragraphs:
        if HEADER_PATTERN.match(p):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = p
            current_lines = [p]
        else:
            current_lines.append(p)
    if current_lines:
        sections.append((current_heading, current_lines))
    return sections


def chunk_document(path):
    filename = os.path.basename(path)
    paragraphs = extract_paragraphs(path)
    press_date = derive_press_date(paragraphs)
    paragraphs = strip_boilerplate(paragraphs)
    paragraphs = [p for p in paragraphs if not is_noise(p)]
    document_title = derive_title(filename)

    sections = split_into_sections(paragraphs)

    chunks = []
    chunk_index = 0
    for heading, lines in sections:
        section_text = "\n".join(lines)
        for part in split_long_text(section_text):
            chunks.append({
                "content": part,
                "embed_text": f"[{document_title}] ({press_date})\n{part}",
                "metadata": {
                    "source_file": filename,
                    "document_title": document_title,
                    "press_date": press_date,
                    "section_heading": heading,
                    "chunk_index": chunk_index,
                },
            })
            chunk_index += 1
    return chunks
