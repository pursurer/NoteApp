"""Build the English reports from verified results and the risk register."""

import csv
import json
from pathlib import Path
import subprocess
import textwrap
from xml.sax.saxutils import escape

from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, PolyLine
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph, Spacer, Table, TableStyle, Image, Preformatted


ROOT = Path(__file__).resolve().parent
COURSE = ROOT.parent.parent
OUT = COURSE / "output/pdf"
TMP = COURSE / "tmp/pdfs"
PROJECT = ROOT / "project1"
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)

def read_json(name):
    return json.loads((ROOT / "results" / name).read_text())

caesar = read_json("caesar_results.json")
image = read_json("image_results.json")
tests = read_json("homework_test_results.json")
env = read_json("environment_verification.json")
migration = read_json("migration_result.json")
assert tests["successful"] and tests["tests_run"] == 17
assert migration["migrated"] == migration["verified"] == 60
assert env["session02_database_unchanged"]
assert caesar["best_shift"] == 11
assert image["gcm_tamper_rejected"]
with (PROJECT / "risks.csv").open() as stream:
    risks = list(csv.DictReader(stream))
with (PROJECT / "flows.csv").open() as stream:
    flows = list(csv.DictReader(stream))
assert set("STRIDE") <= set("".join(r["STRIDE"] for r in risks))
assert all(int(r["Likelihood"]) * int(r["Impact"]) == int(r["Score"]) for r in risks)
assert [r["ID"] for r in sorted(risks, key=lambda r: -int(r["Score"]))[:4]] == ["R01", "R02", "R15", "R03"]
flow_ids = {f["ID"] for f in flows}
linked = set()
for r in risks:
    for part in r["Flow"].split(";"):
        a, _, b = part.partition("-")
        linked.update(str(n) for n in range(int(a), int(b or a) + 1))
assert linked == flow_ids, sorted(flow_ids - linked, key=int)

NAVY = colors.HexColor("#193a5a")
BLUE = colors.HexColor("#087eaa")
LIGHT = colors.HexColor("#edf4f8")
TEXT = colors.HexColor("#243346")
RED = colors.HexColor("#b54d43")
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="ReportTitle", fontName="Helvetica-Bold", fontSize=22,
                          leading=27, textColor=NAVY, spaceAfter=15))
styles.add(ParagraphStyle(name="ReportHeading", fontName="Helvetica-Bold", fontSize=13,
                          leading=17, textColor=BLUE, spaceBefore=10, spaceAfter=7))
styles.add(ParagraphStyle(name="ReportBody", fontName="Helvetica", fontSize=10.3,
                          leading=15, textColor=TEXT, spaceAfter=8))
styles.add(ParagraphStyle(name="ReportSmall", fontName="Helvetica", fontSize=8.6,
                          leading=12, textColor=TEXT, spaceAfter=5))
styles.add(ParagraphStyle(name="ReportCell", fontName="Helvetica", fontSize=8.7,
                          leading=12, textColor=TEXT))
styles.add(ParagraphStyle(name="ReportHeader", fontName="Helvetica-Bold", fontSize=8.7,
                          leading=12, textColor=colors.white))
styles.add(ParagraphStyle(name="ReportCode", fontName="Courier", fontSize=7.8,
                          leading=11, textColor=NAVY, backColor=LIGHT, borderPadding=7,
                          spaceBefore=5, spaceAfter=9))

def p(text, style="ReportBody"):
    return Paragraph(escape(str(text)), styles[style])

def title(text):
    return p(text, "ReportTitle")

def heading(text):
    return p(text, "ReportHeading")

def code(text):
    return Preformatted(text, styles["ReportCode"])

def table(rows, widths):
    data = [[p(cell, "ReportHeader" if i == 0 else "ReportCell") for cell in row]
            for i, row in enumerate(rows)]
    obj = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    obj.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, NAVY),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#d7e2eb")),
    ]))
    return obj

def write_pdf(path, name, pages):
    cv = canvas.Canvas(str(path), pagesize=A4)
    cv.setTitle(name)
    cv.setAuthor("NotesApp coursework")
    for index, (size, elements) in enumerate(pages, 1):
        width, height = size
        cv.setPageSize(size)
        cv.setFillColor(NAVY)
        cv.rect(0, height - 12, width, 12, stroke=0, fill=1)
        cv.setFont("Helvetica-Bold", 8)
        cv.drawString(44, height - 31, "COMPUTER SECURITY / SESSION 03")
        cv.setStrokeColor(colors.HexColor("#d7e2eb"))
        cv.line(44, 39, width - 44, 39)
        cv.setFont("Helvetica", 8)
        cv.setFillColor(TEXT)
        cv.drawString(44, 25, "Updated 22 October 2026 | English report")
        cv.drawRightString(width - 44, 25, f"{index} / {len(pages)}")
        remaining = list(elements)
        frame = Frame(40, 48, width - 80, height - 96, leftPadding=4,
                      rightPadding=4, topPadding=0, bottomPadding=0)
        frame.addFromList(remaining, cv)
        if remaining:
            raise RuntimeError(f"Page {index} overflows: {path.name}; {len(remaining)} blocks remain.")
        cv.showPage()
    cv.save()


def make_diagram():
    d = Drawing(1400, 820)
    def rect(x, y, w, h, fill="white", stroke=NAVY, dashed=False):
        r = Rect(x, y, w, h, rx=9, ry=9, fillColor=colors.toColor(fill),
                 strokeColor=stroke, strokeWidth=1.6)
        if dashed:
            r.strokeDashArray = [7, 5]
        d.add(r)
    def text(x, y, value, size=15, color=TEXT, bold=False):
        d.add(String(x, y, value, fontName="Helvetica-Bold" if bold else "Helvetica",
                     fontSize=size, fillColor=color))
    def box(x, y, w, h, lines, fill="white"):
        rect(x, y, w, h, fill)
        for i, item in enumerate(lines):
            text(x + 13, y + h - 25 - i * 21, item, 16 if i == 0 else 14,
                 NAVY if i == 0 else TEXT, i == 0)
    def boundary(x1, y1, x2, y2):
        line = Line(x1, y1, x2, y2, strokeColor=RED, strokeWidth=2)
        line.strokeDashArray = [7, 5]
        d.add(line)
    def arrow(points, label=None, lx=0, ly=0, both=False):
        d.add(PolyLine(points, strokeColor=BLUE, strokeWidth=2.2))
        def tip(x1, y1, x2, y2):
            import math
            angle = math.atan2(y2-y1, x2-x1)
            a = 0.48
            d.add(Polygon([x2, y2, x2-10*math.cos(angle-a), y2-10*math.sin(angle-a),
                           x2-10*math.cos(angle+a), y2-10*math.sin(angle+a)],
                          fillColor=BLUE, strokeColor=BLUE))
        tip(*points[-4:])
        if both:
            tip(points[2], points[3], points[0], points[1])
        if label:
            text(lx, ly, label, 14, BLUE, True)
    rect(0, 0, 1400, 820, "#f7fafc", stroke=colors.white)
    text(24, 787, "NotesApp data-flow diagram", 26, NAVY, True)
    text(24, 761, "Baseline: the teacher's web/app.py and docker-compose.yml. IDs 1-9 retain the Session 02 flow numbers.", 15)
    rect(20, 330, 210, 370, "#edf4f8")
    text(40, 672, "CLIENT DOMAINS", 14, BLUE, True)
    box(40, 570, 170, 75, ["Student", "Login / own grades"])
    box(40, 465, 170, 75, ["Teacher", "Grades / CSV"])
    box(40, 360, 170, 75, ["Admin", "Users / Ping"])
    rect(330, 330, 500, 370, "#edf4f8")
    text(350, 672, "WEB CONTAINER (RUNS AS ROOT)", 14, BLUE, True)
    box(350, 550, 195, 95, ["Flask", "Routes / identity", "Role checks / SQL"])
    box(600, 390, 190, 85, ["Local files", "Access log", "Image config / backup"])
    rect(340, 365, 215, 100, "#fff7f2", stroke=RED, dashed=True)
    box(350, 375, 195, 80, ["OS shell / Ping", "Same root user", "No process sandbox"])
    text(412, 485, "TB3", 14, RED, True)
    rect(880, 330, 280, 370, "#edf4f8")
    text(900, 672, "DB SERVICE (PORT 5432)", 14, BLUE, True)
    box(895, 550, 215, 95, ["PostgreSQL", "users / classes", "notes / enrollments"])
    box(895, 390, 215, 80, ["DB volume", "Persistent DB files", "Same DB service trust"])
    rect(1220, 330, 165, 370, "#edf4f8")
    text(1235, 672, "NETWORK", 14, BLUE, True)
    box(1232, 540, 142, 105, ["DB client", "Any host that", "reaches TCP", "port 5432"])
    box(350, 190, 195, 65, ["Network target", "Outside app control"])
    rect(560, 110, 270, 160, "#edf4f8")
    text(575, 115, "DOCKER HOST", 14, BLUE, True)
    box(570, 130, 140, 95, ["Docker daemon", "Root on the host", "API: docker.sock"])
    box(718, 130, 105, 95, ["Project tree", "Host source", "Compose, .git"])
    box(880, 140, 230, 85, ["Operator / image config", "Startup settings", "Build-time files"])
    for x, label in ((280, "TB1"), (855, "TB2"), (1195, "TB7")):
        boundary(x, 330, x, 705)
        text(x-18, 715, label, 15, RED, True)
    for x1, x2, label, lx in ((335, 550, "TB4", 414), (560, 826, "TB6", 700), (836, 1160, "TB5", 890)):
        boundary(x1, 316, x2, 316)
        text(lx, 298, label, 14, RED, True)
    arrow([210,620,350,620],"1, 2",245,628)
    arrow([350,596,210,596],"3",245,602)
    # Role requests join the same HTTP entry point.
    arrow([210,515,310,515,310,570,350,570],"4",245,523)
    arrow([350,582,295,582,295,491,210,491],"5",245,497)
    arrow([210,410,320,410,320,558,350,558],"6",245,418)
    arrow([350,594,265,594,265,386,210,386],"7",245,392)
    arrow([545,630,895,630],"8: SQL requests",600,641)
    arrow([895,585,545,585],"9: query results",600,593)
    arrow([500,550,500,515,690,515,690,475],"10: log writes",550,522)
    arrow([390,550,390,455],"11",366,508)
    arrow([470,455,470,550],"12",478,508)
    arrow([390,375,390,255],"13",366,282)
    arrow([470,255,470,375],"14",478,282)
    arrow([990,225,990,282,845,282,845,660,500,660,500,645],"15",812,664)
    arrow([1002,550,1002,470],"16: read / write",1015,504,both=True)
    # The mounts create flows 17-19; the application code does not use them.
    arrow([600,330,600,225],"17",578,282)
    arrow([665,225,665,330],"18",671,282)
    arrow([775,330,775,225],"19",781,282,both=True)
    arrow([1232,615,1110,615],"20",1150,623)
    arrow([1110,575,1232,575],"21",1150,583)
    text(25, 86, "Trust boundaries", 17, NAVY, True)
    text(25, 64, "TB1: browser to web (port 8080 on all host interfaces). TB2: web to DB. TB3: input to OS execution. TB4: Ping to an external target.", 15)
    text(25, 43, "TB5: operator to workload configuration. TB6: root web container to the Docker host (socket and project-tree mounts). TB7: network to the published DB port.", 15)
    text(25, 22, "A boundary marks a trust change, not an effective defense. Logs and DB files remain inside their service trust.", 14)
    return d


diagram = make_diagram()
renderSVG.drawToFile(diagram, str(PROJECT / "data_flow.svg"))
# ReportLab has no PNG backend here; rsvg-convert renders the SVG at 150 dpi.
subprocess.run(["rsvg-convert", "--zoom", str(150 / 72), "--background-color", "white",
                "--output", str(PROJECT / "data_flow.png"), str(PROJECT / "data_flow.svg")],
               check=True)
renderPDF.drawToFile(diagram, str(TMP / "project1_data_flow.pdf"))

W = A4[0] - 88
lab_pages = []
lab_pages.append((A4, [
    title("Class lab and homework"),
    p("Session 03 - Symmetric Encryption | Completed local implementation and verification"),
    p("The assignment is on slide 30. Parts 1 and 2 are class work. Part 3 is homework."),
    table([["Part", "Required work", "Verified result"],
           ["1", "Code Caesar. Recover a message without its key through frequency analysis.", "Recovered shift 11 and the complete practice text."],
           ["2", "Encrypt an image with AES-ECB and AES-GCM. Compare the images.", "ECB retains a visible shape. GCM hides the shape and rejects changed data."],
           ["3", "Encrypt the NotesApp comment column with AES-GCM.", "Migrated 60 comments. All 17 tests passed."],], [32, 252, W-284]),
    heading("Vocabulary"),
    table([["Term", "Meaning in this report"],
           ["Plaintext", "The readable data before encryption."],
           ["Ciphertext", "The output of encryption."],
           ["Key", "The secret value used to encrypt and decrypt."],
           ["Nonce", "A public value that must not repeat with the same GCM key."],
           ["Authentication tag", "The value used to check protected data before decryption returns it."],
           ["Associated data (AAD)", "Context that the tag protects. AAD is not encrypted."],
           ["Symmetric encryption", "Encryption and decryption use the same secret key."],], [136, W-136]),
    heading("Class question: how do two people share a key?"),
    p("Use an authenticated encrypted channel. Verify the colleague's identity first. Use a tested protocol, such as TLS."),
    p("Do not send the key in plaintext. Symmetric encryption alone does not establish trust in the other person."),
    p("Source: Session 03 Symmetric Encryption.pdf, slides 6-8, 25, 27-28 and 30.", "ReportSmall"),
]))

rank_rows = [["Rank", "Encryption shift", "Frequency score"]]
for i, item in enumerate(caesar["candidates"][:3],1):
    rank_rows.append([str(i),str(item["shift"]),f"{item['chi_squared']:.2f}"])
fixture_cipher = (ROOT / "results/caesar_ciphertext.txt").read_text().strip()
fixture_plain = (ROOT / "results/caesar_plaintext.txt").read_text().strip()
lab_pages.append((A4, [
    title("1 / Break Caesar"),
    p("The slides contain no challenge ciphertext. This experiment uses an original practice message with a known verification shift."),
    p("The cracking function receives only the ciphertext. It does not receive the shift or the original message."),
    heading("Method"),
    p("1. Keep letter case, spaces, and punctuation when you apply a shift."),
    p("2. Count the English letters in each candidate plaintext."),
    p("3. Compare the counts with a fixed English frequency table."),
    p("4. Select the shift with the smallest chi-squared score."),
    code("score = sum((observed - expected) ** 2 / expected)\nexpected = letter_count * reference_frequency"),
    table(rank_rows,[55,170,W-225]),
    heading("Ciphertext"),
    code(textwrap.fill(fixture_cipher, 100)),
    heading("Recovered plaintext"),
    p(fixture_plain, "ReportSmall"),
    p(f"Result: shift {caesar['best_shift']}. The ciphertext contains {caesar['letter_count']} English letters.", "ReportSmall"),
    p("The same practice text was recovered for all 26 shifts. Short or unusual messages can give an incorrect frequency rank.", "ReportSmall"),
    p("The most frequent letter is only a clue. This implementation scores all 26 letter counts instead of assuming that one letter represents E.", "ReportSmall"),
]))

lab_pages.append((A4, [
    title("2 / Compare ECB and GCM"),
    p("The input is an original 384 by 288 RGB image. Both modes encrypt the same 331,776 raw pixel bytes."),
    Image(str(ROOT / "results/ecb_gcm_comparison.png"), width=W, height=W*360/1200),
    Spacer(1,10),
    table([["Measurement", "Original", "AES-ECB", "AES-GCM"],
           ["16-byte blocks", "20,736", "20,736", "20,736"],
           ["Unique blocks", "101", "101", "20,736"],
           ["Duplicate block occurrences", "20,635", "20,635", "0"],
           ["Complete encrypted output", "Not applicable", "331,792 bytes", "331,792 bytes"],
           ["Exact decryption", "Input reference", "Passed", "Passed"],
           ["Single-byte change", "Not applicable", "No integrity check", "Rejected"],], [W-228,76,76,76]),
    heading("What the images show"),
    p("ECB gives equal ciphertext blocks for equal plaintext blocks under one key. The repeated areas preserve the outline."),
    p("GCM uses a fresh 12-byte nonce. Its ciphertext preview has no visible outline in this experiment."),
    p("GCM also checks a 16-byte authentication tag. Decryption rejected the changed ciphertext."),
    heading("How the comparison stays valid"),
    p("The program encrypts raw pixels instead of compressed PNG bytes. PNG previews display ciphertext bytes as RGB pixels."),
    p("ECB uses PKCS7 padding. The preview omits the padding. The GCM preview omits its tag."),
    p("The complete encrypted byte files and public metadata are saved separately. The experiment key is discarded after verification."),
    p("No duplicate GCM blocks were observed in this sample. This measurement is not a proof of security."),
    p("Files: results/ecb_gcm_comparison.png, image_results.json, image_metadata.json, and the two encrypted binary files.","ReportSmall"),
]))

lab_pages.append((A4, [
    title("3 / Encrypt NotesApp comments"),
    p("AES and HMAC are integrated into the default web/app.py. The historic 8083 entry point uses the same implementation."),
    code("Teacher input -> encrypt -> PostgreSQL notes.comment\nPostgreSQL notes.comment -> authenticate and decrypt -> page / API / CSV"),
    table([["Item", "Implementation"],
           ["Algorithm", "AES-256-GCM through cryptography.AESGCM."],
           ["Key", "32 random bytes. A separate Docker volume stores the key."],
           ["Nonce", "12 random bytes for each encryption call."],
           ["Tag", "16 bytes, appended by the AESGCM API."],
           ["Database format", "gcm1: + Base64(nonce || ciphertext || tag)."],
           ["Protected context", "AAD = NotesApp:notes:<note_id>:comment:v1."],
           ["Payload", "UTF-8 JSON. This preserves text, empty text, Unicode, and a null comment."],
           ["Read paths", "Student page, teacher page, note API, and both CSV query paths."],
           ["Write paths", "New notes and existing note updates encrypt before storage."],
           ["Failure behavior", "Missing key stops startup. Invalid comments produce a generic error."],], [118,W-118]),
    heading("Existing data"),
    p("The migration locks the notes table. It encrypts comments and verifies the original values inside one transaction."),
    p("A failed check rolls back the transaction. A second migration verifies existing ciphertext without encrypting it again."),
    p("A database constraint rejects missing envelopes and null stored values. Cryptographic verification checks the envelope contents when the application reads them."),
    heading("Key handling"),
    p("The key generator creates the key once with file mode 0600. It does not print or replace the key."),
    p("The launcher loads the persistent key into NOTESAPP_COMMENT_KEY. The app reads the key from this environment variable. The database does not mount the key volume."),
    p("Keep the key volume with the encrypted database. Loss of this key makes its comments unreadable."),
]))

lab_pages.append((A4, [
    title("Verification results"),
    p(f"Original experiment: {env['verified_at'][:10]}, 17 AES tests passed. Integration rechecked on 22 October 2026: 45 checks passed in each existing environment, including AES, HMAC, environment keys, and existing Argon2 behavior."),
    table([["Check", "Result"],
           ["Migration", "60 rows migrated. 60 rows verified. Plaintext digests match."],
           ["Current comment column", "60 of 60 rows have encrypted envelopes. No raw null values remain."],
           ["Round trip", "Normal text, empty text, null, Unicode, and line breaks passed."],
           ["Fresh randomness", "Two equal comments received different nonces and ciphertext."],
           ["Invalid data", "Changed nonce, ciphertext, tag, wrong key, wrong row, and malformed envelope were rejected."],
           ["Application writes", "Teacher create and update paths stored encrypted comments."],
           ["Application reads", "Student page, teacher page, API, and both CSV paths returned plaintext."],
           ["Startup and migration", "A missing key stopped startup. A repeat migration made no changes."],
           ["Data preservation", "The original experiment kept Session 02 unchanged. The October 22 default-app migration preserved logical values; see the acceptance record."],], [152,W-152]),
    heading("Normal HTTP checks"),
    p("Four additional checks used the running server and the seeded student and teacher accounts. They covered login, pages, API, and CSV."),
    p("All four checks returned HTTP 200. Comments appeared as plaintext in the expected responses. Stored envelopes did not appear in those responses."),
    heading("Evidence files"),
    p("results/homework_test_results.json lists the 17 tests. results/migration_result.json records the migration outcome."),
    p("results/environment_verification.json records normal HTTP checks, row counts, volume access, and the baseline database check."),
    p("Application integration tests used Flask test clients and the real PostgreSQL service. Temporary test rows were deleted after each test."),
    p("These tests verify comment encryption. They do not establish that the course authentication or authorization is secure."),
]))

lab_pages.append((A4, [
    title("Run and review the work"),
    p("Run these commands from the NoteApp directory. Use a separate project name for the homework."),
    code("docker compose -p notesapp-session03 -f compose.session03.yml \\\n  up -d --build --wait\n\ndocker compose -p notesapp-session03 -f compose.session03.yml \\\n  exec -T web python runtime.py python test_homework.py"),
    p("Open http://127.0.0.1:8083. Use the seeded course accounts listed in the original README."),
    p("Use Python with cryptography and Pillow for the class scripts."),
    code("python3 session03/make_caesar_fixture.py\npython3 session03/caesar.py session03/results/caesar_ciphertext.txt \\\n  --output session03/results/caesar_results.json\npython3 session03/image_modes.py"),
    heading("Protection limits"),
    p("The key protects comments in a copied current table when the attacker cannot obtain the key. Names, grades, and record structure remain visible."),
    p("Encryption does not fix the course login, access control, CSRF, active HTML, or command execution flaws."),
    p("The application decrypts comments before it returns them. An unauthorized application response can still disclose plaintext."),
    p("GCM exposes message length. It does not prevent replay of an older valid value for the same row."),
    p("Earlier backups, database history, and the seed SQL can retain plaintext. This lab does not erase those copies."),
    p("A compromised web process can use its mounted key. Production key isolation, rotation, and backup policies need separate work."),
    heading("References"),
    p("Course source: Session 03 Symmetric Encryption.pdf, slides 25, 27-28 and 30.", "ReportSmall"),
    p("AESGCM API: https://cryptography.io/en/50.0.0/hazmat/primitives/aead/", "ReportSmall"),
    p("GCM: https://csrc.nist.gov/pubs/sp/800/38/d/final", "ReportSmall"),
]))

write_pdf(OUT / "Session03-Lab-and-Homework.pdf", "Session 03 - Class lab and homework", lab_pages)

project_pages=[]
project_pages.append((A4,[
    title("Project 1 / NotesApp risk analysis"),
    p("ZIQIAN YU / 2023902046 | HAOJIE SONG / 2023905496", "ReportSmall"),
    p("The required outputs are on slide 31: a data-flow diagram, STRIDE coverage, risk scores, and fixes for the top three risks."),
    heading("Scope and assets"),
    p("Code references resolve inside the baseline/ evidence snapshot of the original course application. The baseline Git commit is " + env["baseline_git_commit"] + ".", "ReportSmall"),
    p("Protect student identities, grades, private comments, account credentials, session data, audit records, and service availability."),
    p("The teacher's Compose file publishes web port 8080 and DB port 5432 on all host interfaces. The web container runs as root and mounts the host Docker socket and the project tree."),
    p("The model includes student, teacher, admin, operator, browser, web, database, local files, the Ping target, the Docker host, and network DB clients."),
    p("Runtime DB checks used a loopback-only local overlay. The overlay changes ports, mounts, networks, and resource limits. It does not change DB settings.", "ReportSmall"),
    p("Sources confirm code paths and configuration. The analysis does not claim successful attacks or measured denial of service."),
    heading("Risk method"),
    p("Score = likelihood x impact. These ordinal scores are analyst estimates, not measured probabilities. Shared causes can connect several threats."),
    table([["Level", "Likelihood after the stated prerequisite", "Impact"],
           ["1", "Rare. Strong additional conditions are necessary.", "Minor disruption or low-sensitivity data."],
           ["2", "Unlikely. Requires control of a restricted path.", "Limited disruption or a small reversible change."],
           ["3", "Plausible. Requires an account, data access, or several conditions.", "Material service disruption or data changes."],
           ["4", "Likely. Few controls resist a capable actor.", "Broad private-data disclosure or grade changes."],
           ["5", "Direct path with low effort once the prerequisite holds.", "Admin, OS, or DB control; broad account compromise."],], [38,252,W-290]),
    p("High: 15-25. Medium: 6-14. Low: 1-5. Equal scores do not establish a meaningful difference in risk.","ReportSmall"),
    heading("Top three"),
    p("R01: forged identities, score 25. R02: login SQL injection, score 25. R15: direct DB login through the published port, score 25."),
    p("The three tie. Each one bypasses the identity or access checks of the application. R03, missing record scope, follows with 20."),
]))

scaled = Drawing(diagram.width,diagram.height)
scaled.add(diagram)
factor=min((landscape(A4)[0]-88)/diagram.width, (landscape(A4)[1]-150)/diagram.height)
scaled.scale(factor,factor)
scaled.width=diagram.width*factor
scaled.height=diagram.height*factor
scaled.hAlign="CENTER"
project_pages.append((landscape(A4),[
    title("Data flow and trust boundaries"),scaled,
]))

flow_rows=[["ID","Sender -> receiver","Data / boundary"]]
for f in flows:
    flow_rows.append([f["ID"],f["Sender"]+" -> "+f["Receiver"],f["Data"]+". "+f["Boundary"]])
project_pages.append((A4,[
    title("Numbered flow register"),
    p("The diagram groups related browser traffic. The register states the data and direction of each numbered flow."),
    table(flow_rows,[28,160,W-188]),
    p("Flows 13 and 14 are inferred from the Ping code. No packet capture or external Ping test was performed.","ReportSmall"),
    p("Flows 17-19 exist because of the Compose mounts. The application code does not use them; any process in the root container can. Flows 20-21 come from any client that reaches the published DB port.","ReportSmall"),
    p("Local logs and DB files share their service trust. TB3 marks command execution; the baseline provides no process sandbox.","ReportSmall"),
]))

short_fixes={
    "R01":"Reject unsigned JWTs. Use tested verification and independent random signing keys.",
    "R02":"Use parameterized SQL, password hashes, and a restricted DB role.",
    "R03":"Apply student and teacher ownership checks to every affected path.",
    "R04":"Use AES-GCM and separate keys. Control old plaintext copies.",
    "R05":"Remove shell=True. Validate the host and restrict OS privileges.",
    "R06":"Enable HTML autoescape. Sanitize only approved rich text.",
    "R07":"Check CSRF tokens on state changes. Set suitable cookie attributes.",
    "R08":"Record sensitive actions and protect audit storage.",
    "R09":"Hash passwords. Remove bundled credential backups. Restrict secrets.",
    "R10":"Use verified HTTPS for network access.",
    "R11":"Use verified DB TLS where required. Restrict DB connectivity.",
    "R12":"Limit requests, result size, database work, and execution time.",
    "R13":"Disable debugging. Return generic errors. Protect diagnostics.",
    "R14":"Use a DB role with only required table and sequence privileges.",
    "R15":"Close the DB port. Keep the DB on an internal network. Use a secret password and a least-privilege role.",
    "R16":"Remove the socket and project-tree mounts. Run as a non-root user. Drop capabilities.",
    "R17":"Allow only approved targets. Block internal ranges. Rate-limit Ping.",
    "R18":"Treat Ping output as a hint. Prefer IP targets. Use an authenticated health check.",
}
register_notes={
    1:["R01 has two paths. An unsigned JWT affects API identity. A forged Flask session can affect session-only teacher or admin routes."],
    2:["The teacher's Compose file publishes the HTTP port on all host interfaces and sets no resource limits."],
    3:["DB role flags were checked directly: the application login is a superuser and can create databases and roles. No privileged operation was attempted.",
       "R15 is the direct network path to the database. R04, R09, and R14 cover copies and SQL paths through the application. No DB login, host access, or network probe was attempted."],
}
for page_number, part in enumerate((risks[:6],risks[6:12],risks[12:]),1):
    risk_rows=[["ID / STRIDE","Flows","Scenario and prerequisite","L / I / score","Proposed fix"]]
    for r in part:
        risk_rows.append([r["ID"]+" / "+r["STRIDE"],r["Flow"].replace(";",", "),
                          r["Threat"]+". Requires: "+r["Prerequisite"]+".",
                          f"{r['Likelihood']} / {r['Impact']} / {r['Score']}",short_fixes[r["ID"]]])
    elements=[title(f"STRIDE risk register / {page_number}"),
              p("S: Spoofing. T: Tampering. R: Repudiation. I: Information disclosure. D: Denial of service. E: Elevation of privilege. Flows are the numbered flows of the diagram.","ReportSmall"),
              table(risk_rows,[62,46,180,52,W-340]),heading("Evidence and confidence")]
    for r in part:
        elements.append(p(r["ID"]+": "+r["Evidence"]+". "+r["Status"]+".","ReportSmall"))
    for note in register_notes[page_number]:
        elements.append(p(note,"ReportSmall"))
    project_pages.append((A4,elements))

project_pages.append((A4,[
    title("Fix the top three risks"),
    p("These are proposed fixes for the original course baseline. The implemented Session 03 change protects the comment column."),
    heading("1. R01 / Trust verified identities"),
    p("Reject alg:none and unexpected token algorithms. Use a maintained token verifier with required claim checks and expiry."),
    p("Generate independent random signing keys for tokens and Flask sessions. Store them outside source code. Invalidate sessions signed with old demo keys."),
    p("Acceptance check: reject unsigned or altered tokens. Reject old forged sessions. Confirm that valid users retain their permitted access."),
    heading("2. R02 / Separate input from SQL"),
    p("Use SQL parameters for the login fields. Verify a password hash instead of comparing a stored plaintext password."),
    p("Give the application DB login only the required table and sequence permissions. Remove superuser and role-management authority."),
    p("Acceptance check: login input cannot change SQL structure. Valid logins work. Invalid credentials fail. The app role cannot manage DB roles."),
    heading("3. R15 / Close the database to the network"),
    p("Remove the published 5432 port. Keep PostgreSQL on an internal Docker network. Keep the DB password outside the repository. Give the app a non-superuser role."),
    p("Acceptance check: a client outside the Docker network cannot open TCP 5432. The old published password fails. The app still reads and writes grades."),
    p("Next: R03, missing record scope (20). Check student note ownership and teacher class ownership on every read, write, page, and export.","ReportSmall"),
    heading("Effect of the completed encryption homework"),
    p("AES-GCM addresses the comment-copy scenario in R04 when the key is unavailable to the attacker. With it, a direct DB login (R15) reads only comment ciphertext; names, grades, and passwords stay exposed."),
    p("The homework does not establish lower risk for R01, R02, R03, or R15. The web application still decrypts comments after its existing identity and access checks."),
    heading("Presentation and files"),
    p("The three-minute speaking outline is in project1/PRESENTATION-3min.md. Editable evidence is in flows.csv, risks.csv, and data_flow.svg."),
    p("Source: Session 03 Symmetric Encryption.pdf, slide 31. STRIDE definitions: https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats", "ReportSmall"),
]))
write_pdf(OUT / "Session03-Project1-Risk-Analysis.pdf", "Project 1 - NotesApp risk analysis",project_pages)


def markdown_table(headers, rows):
    def cell(value):
        return str(value).replace("|","/").replace("\n"," ")
    return "\n".join(["| "+" | ".join(headers)+" |",
                       "| "+" | ".join("---" for _ in headers)+" |"]+
                      ["| "+" | ".join(cell(v) for v in row)+" |" for row in rows])

lab_md=f'''# Session 03 - Class lab and homework

Date: 8 October 2026. Updated: 22 October 2026. Source: `Session 03 Symmetric Encryption.pdf`, slide 30.

## Result

The three parts are complete in the local homework environment.

- Caesar: recovered shift {caesar['best_shift']} and the complete practice message.
- Image: ECB retained a visible outline. GCM hid the outline and rejected a changed byte.
- NotesApp: encrypted and verified 60 comments. All 17 tests passed.

## 1. Break Caesar

The slides give no challenge ciphertext. This experiment uses an original practice message.
The cracking function receives only ciphertext. It receives neither the key nor the original message.

Count the English letters for each of the 26 shifts.
Compare each distribution with a fixed English frequency table.
Select the smallest chi-squared score.

`score = sum((observed - expected)^2 / expected)`

`expected = letter_count * reference_frequency`

{markdown_table(['Rank','Shift','Score'],[[i+1,r['shift'],f"{r['chi_squared']:.2f}"] for i,r in enumerate(caesar['candidates'][:3])])}

Ciphertext:

```text
{fixture_cipher}
```

Recovered plaintext:

> {fixture_plain}

The same practice text passed all 26 shifts. Short or unusual messages can produce the wrong rank.
The most common letter is only a clue. Use the full distribution instead of relying on E alone.

## 2. Compare ECB and GCM

![Original, ECB, and GCM](results/ecb_gcm_comparison.png)

The input contains 331,776 raw RGB bytes. Both modes use the same image and the same experiment key.
The original image and ECB output each have 101 unique blocks among 20,736 blocks.
The GCM output has 20,736 unique blocks in this run.

ECB maps equal input blocks to equal output blocks. GCM hides the visible shape and checks an authentication tag.
Both modes recovered the exact original pixels. GCM rejected the changed ciphertext.

The program encrypts raw pixels. It does not encrypt compressed PNG file bytes.
PNG previews omit ECB padding and the GCM tag.
The complete encrypted byte files and public metadata are separate.
The key is discarded after verification. Rerun the script to repeat encryption and decryption.

## 3. Encrypt the NotesApp comment column

- Use AES-256-GCM with a 32-byte key.
- Generate a fresh 12-byte random nonce for each encryption.
- Store `gcm1:` followed by Base64 of `nonce || ciphertext || tag`.
- Use `NotesApp:notes:<note_id>:comment:v1` as associated data.
- Encrypt UTF-8 JSON to preserve text, empty text, Unicode, and null comments.
- Encrypt before insert or update. Reserve a new row ID before encryption.
- Authenticate and decrypt on the student, teacher, API, and CSV read paths.
- Stop startup if the key is absent. Reject invalid ciphertext with a generic error.

The migration uses a table lock and one transaction. It verifies all recovered values before commit.
A repeat migration verifies existing ciphertext without encrypting it again.
A database constraint rejects plaintext writes and raw null values.

The key generator creates a separate Docker key volume once. The file mode is 0600.
The launcher exports it as NOTESAPP_COMMENT_KEY. The application reads this environment variable. The DB service does not mount the key volume.
The key is not printed, exported, or included in the submission files.
Keep the key volume with the encrypted database. Key loss makes the comments unreadable.

## Verification

All 17 tests passed. They cover seven cipher tests and ten PostgreSQL application tests.
Four normal HTTP checks covered seeded student and teacher login, pages, API, and CSV.
The database has 60 encrypted comments and no raw null comment values.
The original October 8 experiment preserved the Session 02 database. On October 22, the default application was also migrated; see the current acceptance record.

Evidence:

- `results/caesar_results.json` and `caesar_verification.json`.
- `results/image_results.json` and `image_metadata.json`.
- `results/homework_test_results.json`.
- `results/migration_result.json`.
- `results/environment_verification.json`.

## Protection limits

Encryption protects the current comment column when the attacker cannot obtain its key.
Names, grades, and record structure remain visible.
GCM does not hide message length or prevent same-row replay of an older valid comment.
Earlier backups, database history, and seed SQL can retain plaintext.
The existing course login, access control, CSRF, active HTML, and command flaws remain.
A compromised web process can use its mounted key.
Production key isolation, rotation, and backup policies need separate work.

## Class question: how can colleagues share a key?

Use an authenticated encrypted channel. Verify the colleague's identity first.
Use a tested protocol, such as TLS. Do not send the key in plaintext.
Symmetric encryption alone does not establish trust in the other person.

## References

- Course slides: 6-8, 25, 27-28 and 30.
- [AESGCM API](https://cryptography.io/en/50.0.0/hazmat/primitives/aead/).
- [NIST GCM specification](https://csrc.nist.gov/pubs/sp/800/38/d/final).
'''
(ROOT / "REPORT.md").write_text(lab_md)

project_md='''# Project 1 - NotesApp risk analysis

Date: 8 October 2026. Updated: 22 October 2026. Course source: `Session 03 Symmetric Encryption.pdf`, actual PDF page 31.

**Group:** ZIQIAN YU (2023902046); HAOJIE SONG (2023905496).

## Scope

The baseline is the teacher's original `web/app.py` and `docker-compose.yml`. All code references below resolve inside `baseline/`, a pinned evidence snapshot. They do not refer to the updated application.
The Git baseline is `'''+env["baseline_git_commit"]+'''`.
The Compose file publishes web port 8080 and DB port 5432 on all host interfaces.
The web container runs as root and mounts the host Docker socket and the project tree.
Runtime DB checks used the loopback-only local overlay `compose.lab.yml`. The overlay changes ports, mounts, networks, and resource limits. It does not change DB settings.

Protect identities, grades, comments, credentials, sessions, audit records, and availability.
Code and configuration support the listed threats. No exploit or load test was run for this analysis.
C3 and C4 now run in the default application. The historic 8083 environment remains available with its own database and keys. This risk analysis still describes the original baseline.

## Data-flow diagram

![Complete baseline data flow](data_flow.png)

`data_flow.svg` is the editable vector version. The first nine flow IDs retain the Session 02 numbering.

- TB1: browser to web service.
- TB2: web service to PostgreSQL.
- TB3: application input to OS command execution. The baseline has no process sandbox.
- TB4: OS Ping to an external network target.
- TB5: trusted operator to workload settings and image files.
- TB6: root web container to the Docker host, through the Docker socket and project-tree mounts.
- TB7: any network client to the published PostgreSQL port.

Logs and DB files share the trust of their services. A drawn boundary is not proof of an effective defense.
`flows.csv` lists 21 numbered flows: browser requests, CSV, audit files, Ping, startup settings, DB persistence, the host mounts, and direct DB clients.
The Ping network flows are inferred from code. They were not captured.
Flows 17-19 exist because of the Compose mounts. The application code does not use them; any process in the root container can.
Flows 20-21 come from any client that reaches the published DB port.

## Risk method

Score = likelihood x impact. Each value uses a scale from 1 to 5.
These are analyst estimates, not measured attack probabilities.
Likelihood describes ease after the stated prerequisite. Impact describes the resulting loss.

Likelihood: 1 rare, 2 restricted path, 3 plausible with conditions, 4 few resisting controls, 5 direct low-effort path.
Impact: 1 minor, 2 limited, 3 material disruption, 4 broad private-data or grade loss, 5 admin/OS/DB control.

High: 15-25. Medium: 6-14. Low: 1-5.
Equal scores do not establish a meaningful difference in risk. Related threats can share causes.

## STRIDE register

S = Spoofing. T = Tampering. R = Repudiation.
I = Information disclosure. D = Denial of service. E = Elevation of privilege.

'''+markdown_table(["ID","STRIDE","Flows","Threat","Prerequisite","L","I","Score","Fix","Evidence"],
    [[r["ID"],r["STRIDE"],r["Flow"].replace(";",", "),r["Threat"],r["Prerequisite"],r["Likelihood"],r["Impact"],r["Score"],r["Fix"],r["Evidence"]] for r in risks])+'''

Each row in `risks.csv` also states its evidence status. The register covers all six STRIDE letters, and every numbered flow appears in at least one row.
R01 has two paths. An unsigned JWT affects API identity.
A forged Flask session can affect session-only teacher or admin gates.
The application DB role is a superuser and can create databases and roles.
These role flags were checked directly. No privileged operation was attempted.
R15 is the direct network path to the database. R04, R09, and R14 cover copies and SQL paths through the application.
No DB login, host access, or network probe was attempted.

## Top three risks and proposed fixes

### R01 - Forge an identity: 25

Reject unsigned and unexpected JWT algorithms. Use a maintained verifier and check required claims and expiry.
Generate independent random signing keys for tokens and Flask sessions. Keep the keys outside source code.
Invalidate sessions signed with the old demo keys.

Acceptance checks: reject unsigned tokens, changed tokens, and old forged sessions.
Confirm that valid users retain their permitted access.

### R02 - Login SQL injection: 25

Parameterize the login query. Verify a password hash.
Use a non-superuser DB role with only the required table and sequence grants.

Acceptance checks: input cannot change SQL structure. Valid logins work. Invalid credentials fail.
The application DB role cannot manage other roles.

### R15 - Direct DB login through the published port: 25

Remove the published 5432 port. Keep PostgreSQL on an internal Docker network that only the web service can reach.
Generate the DB password outside the repository and pass it as a secret.
Give the application a non-superuser role with only the required grants.

Acceptance checks: a client outside the Docker network cannot open TCP 5432. The old published password fails.
The application still reads and writes grades.

R01, R02, and R15 tie. Each one bypasses the identity or access checks on which other defenses depend.
R03, missing record scope, follows with 20: check student note ownership and teacher class ownership on every read, write, page, and export.
The fixes above are proposals for the course baseline. They are not implemented by this risk report.

## Effect of Session 03 encryption

The homework addresses R04 for the current comment column when its key is unavailable to the attacker.
With it, a direct DB login (R15) reads only comment ciphertext; names, grades, and passwords stay exposed.
It does not establish a reduced risk for R01, R02, R03, or R15. The application still decrypts comments for its responses.
Other fields, old plaintext copies, and web-process key access remain relevant.

## Presentation and files

Use `PRESENTATION-3min.md` as the three-minute speaking outline.
Editable evidence is in `flows.csv`, `risks.csv`, and `data_flow.svg`.

## References

- Original `web/app.py`, `web/templates`, `web/Dockerfile`, `db/init.sql` and `docker-compose.yml`.
- Current baseline checks: DB TLS off and application DB role flags.
- [Microsoft STRIDE definitions](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats).
- Course slide 31.
'''
(PROJECT / "REPORT.md").write_text(project_md)
print("Created the lab and Project 1 PDF reports, Markdown sources, and the data-flow diagram (SVG and PNG).")


if __name__ == "__main__":
    pass
