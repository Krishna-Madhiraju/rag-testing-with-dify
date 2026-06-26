"""
Generates the Orion Technologies Employee Handbook PDF.
Run: python3.11 generate_handbook.py
Output: orion-technologies-employee-handbook.pdf
"""

from fpdf import FPDF


COMPANY = "Orion Technologies, Inc."
PRIMARY = (30, 64, 175)    # deep blue
ACCENT  = (79, 70, 229)    # indigo
LIGHT   = (241, 245, 249)  # slate-50
BLACK   = (15, 23, 42)
GREY    = (100, 116, 139)


class HandbookPDF(FPDF):

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*PRIMARY)
        self.rect(0, 0, 210, 12, "F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 3)
        self.cell(0, 6, f"{COMPANY}  |  Employee Handbook  |  Confidential", align="L")
        self.set_xy(10, 3)
        self.cell(0, 6, f"Page {self.page_no()}", align="R")
        self.ln(8)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*GREY)
        self.set_xy(10, self.get_y() + 2)
        self.cell(0, 5, "© 2025 Orion Technologies, Inc. -- All rights reserved. This handbook is for internal use only.")

    # ── helpers ─────────────────────────────────────────────────────────────

    def cover(self):
        self.add_page()
        # top band
        self.set_fill_color(*PRIMARY)
        self.rect(0, 0, 210, 80, "F")
        # logo placeholder
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(255, 255, 255)
        self.set_xy(0, 20)
        self.cell(0, 18, "ORION", align="C")
        self.set_font("Helvetica", "", 13)
        self.set_text_color(199, 210, 254)
        self.set_xy(0, 40)
        self.cell(0, 8, "TECHNOLOGIES, INC.", align="C")
        self.set_xy(0, 52)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 6, "Building tomorrow's infrastructure, today.", align="C")
        # title block
        self.set_fill_color(*ACCENT)
        self.rect(30, 88, 150, 30, "F")
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(255, 255, 255)
        self.set_xy(30, 93)
        self.cell(150, 10, "EMPLOYEE HANDBOOK", align="C")
        self.set_font("Helvetica", "", 10)
        self.set_xy(30, 105)
        self.cell(150, 8, "Effective Date: January 1, 2025", align="C")
        # meta
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*BLACK)
        lines = [
            "Orion Technologies, Inc.",
            "1420 Innovation Drive, Suite 900",
            "Austin, Texas 78701",
            "hr@oriontech.io  |  +1 (512) 400-7200",
            "www.oriontech.io",
        ]
        y = 135
        for line in lines:
            self.set_xy(0, y)
            self.cell(0, 6, line, align="C")
            y += 7
        # version note
        self.set_xy(0, 240)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*GREY)
        self.cell(0, 6, "Version 4.2  |  Supersedes all prior versions  |  Confidential -- Do not distribute externally", align="C")

    def toc_page(self, sections):
        self.add_page()
        self.chapter_title("Table of Contents")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*BLACK)
        for num, title, page in sections:
            self.set_x(15)
            dots = "." * max(2, 70 - len(f"{num}  {title}"))
            self.cell(0, 7, f"  {num}  {title}  {dots}  {page}", ln=True)

    def chapter_title(self, text, add_rule=True):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*PRIMARY)
        self.set_x(10)
        self.cell(0, 10, text, ln=True)
        if add_rule:
            self.set_draw_color(*ACCENT)
            self.set_line_width(0.8)
            x = self.get_x()
            y = self.get_y()
            self.line(10, y, 200, y)
            self.ln(4)
        self.set_text_color(*BLACK)

    def section_heading(self, text):
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(*LIGHT)
        self.set_text_color(*PRIMARY)
        self.set_x(10)
        self.cell(190, 7, f"  {text}", fill=True, ln=True)
        self.set_text_color(*BLACK)
        self.ln(1)

    def sub_heading(self, text):
        self.ln(2)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*ACCENT)
        self.set_x(10)
        self.cell(0, 6, text, ln=True)
        self.set_text_color(*BLACK)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*BLACK)
        self.set_x(10)
        self.multi_cell(190, 5.5, text)
        self.ln(2)

    def bullet(self, items, indent=14):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*BLACK)
        for item in items:
            self.set_x(indent)
            self.cell(5, 5.5, "*")
            self.set_x(indent + 5)
            self.multi_cell(185 - indent, 5.5, item)

    def table(self, headers, rows, col_widths=None):
        if col_widths is None:
            w = 190 // len(headers)
            col_widths = [w] * len(headers)
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*PRIMARY)
        self.set_text_color(255, 255, 255)
        self.set_x(10)
        for h, w in zip(headers, col_widths):
            self.cell(w, 7, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 9)
        fill = False
        for row in rows:
            self.set_fill_color(241, 245, 249) if fill else self.set_fill_color(255, 255, 255)
            self.set_text_color(*BLACK)
            self.set_x(10)
            for cell, w in zip(row, col_widths):
                self.cell(w, 6, cell, border=1, fill=True)
            self.ln()
            fill = not fill
        self.ln(3)

    def info_box(self, label, text):
        self.set_fill_color(239, 246, 255)
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.3)
        self.set_x(10)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*ACCENT)
        self.cell(190, 6, f"  {label}", border="LTR", fill=True, ln=True)
        self.set_x(10)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*BLACK)
        self.multi_cell(190, 5, f"  {text}", border="LBR")
        self.ln(3)

    def new_chapter(self, title):
        self.add_page()
        self.chapter_title(title)


# ═══════════════════════════════════════════════════════════════════════════
# CONTENT
# ═══════════════════════════════════════════════════════════════════════════

pdf = HandbookPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(10, 14, 10)

# ── Cover ──────────────────────────────────────────────────────────────────
pdf.cover()

# ── TOC (approximate pages) ───────────────────────────────────────────────
toc = [
    ("1",   "Welcome to Orion Technologies",            3),
    ("2",   "Employment Policies",                      5),
    ("3",   "Code of Conduct & Ethics",                 8),
    ("4",   "Work Hours, Attendance & Remote Work",    11),
    ("5",   "Compensation & Payroll",                  13),
    ("6",   "Employee Benefits",                       15),
    ("7",   "Time Off & Leave Policies",               18),
    ("8",   "Performance, Growth & Development",       21),
    ("9",   "Information Technology & Security",       23),
    ("10",  "Workplace Health & Safety",               25),
    ("11",  "Anti-Harassment & Non-Discrimination",    27),
    ("12",  "Disciplinary Procedures",                 29),
    ("13",  "Separation & Offboarding",                31),
    ("14",  "Acknowledgment of Receipt",               33),
]
pdf.toc_page(toc)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 1 -- Welcome
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("1.  Welcome to Orion Technologies")

pdf.section_heading("1.1  A Message from Our CEO")
pdf.body(
    "Dear Orion Team Member,\n\n"
    "Welcome aboard -- we are genuinely thrilled to have you with us. Whether you are joining Orion "
    "for the first time or returning after a break, you are now part of a team of over 1,200 people "
    "spread across twelve countries who wake up every day determined to build infrastructure software "
    "that makes the modern internet faster, safer, and more reliable.\n\n"
    "This handbook is your guide to how we work together. It documents the policies, benefits, and "
    "expectations that form the foundation of life at Orion. We have tried to write it in plain language "
    "rather than legalese, because we believe you deserve to understand your rights and responsibilities "
    "without needing a lawyer by your side.\n\n"
    "Please read it carefully, ask questions whenever something is unclear, and know that every policy "
    "here was crafted with one goal in mind: to create a workplace where exceptional people can do the "
    "best work of their careers.\n\n"
    "With gratitude,\n\n"
    "Priya Nandakumar\nChief Executive Officer, Orion Technologies, Inc."
)

pdf.section_heading("1.2  Our Story")
pdf.body(
    "Orion Technologies was founded in 2011 by three engineers -- Priya Nandakumar, Marcus Webb, and "
    "Yuki Tanaka -- in a two-bedroom apartment in Austin, Texas. The founding idea was simple: cloud "
    "infrastructure tooling was too complex, too fragile, and too expensive for the majority of "
    "engineering teams that needed it.\n\n"
    "The company launched its first product, OrionGrid, in 2013 -- a distributed task scheduler that "
    "reduced infrastructure costs by an average of 40% for its first 50 customers. By 2016, Orion had "
    "raised Series B funding, expanded to Europe, and grown to 150 employees. Today, Orion serves over "
    "8,000 enterprise customers across financial services, healthcare, e-commerce, and government sectors, "
    "processing more than 4 trillion events per month on its platform.\n\n"
    "We went public on the NASDAQ (ticker: ORNX) in 2022 and have been profitable every quarter since."
)

pdf.section_heading("1.3  Mission, Vision & Values")
pdf.sub_heading("Mission")
pdf.body("To make powerful infrastructure technology accessible to every engineering team on Earth.")

pdf.sub_heading("Vision")
pdf.body("A world where software reliability is a given, not a luxury.")

pdf.sub_heading("Our Five Core Values")
pdf.bullet([
    "Craft -- We take pride in our work and hold ourselves to a high standard of quality.",
    "Transparency -- We default to openness. Information flows freely at Orion.",
    "Customer obsession -- Every decision starts with the question: does this make our customers more successful?",
    "Inclusion -- We build a workforce as diverse as the world we serve.",
    "Accountability -- We own our outcomes, celebrate our wins, and learn from our failures without blame.",
])

pdf.section_heading("1.4  About This Handbook")
pdf.body(
    "This handbook applies to all regular full-time and part-time employees of Orion Technologies, Inc. "
    "and its wholly-owned subsidiaries. It does not constitute an employment contract and does not alter "
    "the at-will nature of employment at Orion (see Section 2.1).\n\n"
    "Orion reserves the right to amend, modify, or rescind any policy in this handbook at any time, with "
    "or without notice. The most current version is always available on the Orion People Portal at "
    "people.oriontech.io. When this handbook is updated, employees will be notified by email and will be "
    "required to acknowledge the updated version within 14 days."
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 2 -- Employment Policies
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("2.  Employment Policies")

pdf.section_heading("2.1  At-Will Employment")
pdf.body(
    "Employment at Orion Technologies is at-will, meaning either the employee or Orion may end the "
    "employment relationship at any time, for any lawful reason or no reason at all, with or without "
    "notice. Nothing in this handbook, any offer letter, or any verbal statement by a manager creates "
    "a contract of employment for a definite term.\n\n"
    "The at-will nature of employment at Orion can only be modified by a written agreement signed by "
    "the Chief Executive Officer or Chief People Officer."
)

pdf.section_heading("2.2  Equal Opportunity Employment")
pdf.body(
    "Orion Technologies is an equal opportunity employer. We do not discriminate in hiring, promotion, "
    "compensation, benefits, training, termination, or any other term of employment on the basis of "
    "race, color, religion, sex (including pregnancy, gender identity, and sexual orientation), national "
    "origin, age (40 or over), disability, genetic information, veteran status, or any other characteristic "
    "protected by applicable federal, state, or local law.\n\n"
    "This commitment applies to all employment decisions made by all employees at all levels. Any employee "
    "who believes they have experienced or witnessed discrimination is encouraged to report it immediately "
    "using the process described in Section 11."
)

pdf.section_heading("2.3  Employment Classifications")
pdf.table(
    ["Classification", "Hours per Week", "Benefits Eligible", "Description"],
    [
        ["Full-Time Regular",   "40+",    "Yes (full)",    "Permanent position, ongoing basis"],
        ["Part-Time Regular",   "20-39",  "Yes (pro-rata)","Permanent position, reduced hours"],
        ["Part-Time Limited",   "< 20",   "Limited",       "Ongoing, fewer than 20 hrs/week"],
        ["Fixed-Term",          "Varies", "Yes (full)",    "Time-limited project or role"],
        ["Intern / Co-op",      "Varies", "No",            "Student placement, typically 12-16 wks"],
    ],
    col_widths=[42, 32, 36, 80],
)
pdf.body(
    "Independent contractors and consultants engaged by Orion are not employees and are not covered by "
    "this handbook. Their terms are governed by their individual service agreements."
)

pdf.section_heading("2.4  Introductory Period")
pdf.body(
    "All new regular employees serve a 90-day introductory period beginning on their first day of work. "
    "This period gives both the employee and Orion an opportunity to assess fit and performance. During "
    "this time, employees have access to all standard benefits but may not participate in certain programs "
    "such as the annual promotion cycle or tuition reimbursement.\n\n"
    "Completion of the introductory period does not alter the at-will nature of employment."
)

pdf.section_heading("2.5  Background Checks")
pdf.body(
    "All offers of employment are contingent on the successful completion of a background check, which "
    "may include criminal history, employment verification, education verification, and where applicable "
    "to the role, credit history and professional licence verification.\n\n"
    "Background checks are conducted by a third-party provider in compliance with the Fair Credit "
    "Reporting Act (FCRA). Candidates are provided with all required notices and have the right to dispute "
    "any adverse information before a final employment decision is made."
)

pdf.section_heading("2.6  Immigration & Work Authorization")
pdf.body(
    "Orion is committed to employing only individuals who are legally authorized to work in the country "
    "of employment. All new hires must complete Form I-9 (in the United States) or the equivalent "
    "documentation for their location within three business days of their start date.\n\n"
    "Orion sponsors H-1B, O-1, TN, and other work authorisation categories on a case-by-case basis "
    "depending on role requirements and business need. Employees who require visa sponsorship must notify "
    "the People team at least 180 days before their current authorisation expires."
)

pdf.section_heading("2.7  Rehire Policy")
pdf.body(
    "Former employees who left Orion in good standing (eligible for rehire) may be considered for open "
    "positions. Prior service is generally not credited for purposes of benefits eligibility or PTO "
    "accrual unless specifically negotiated in the offer letter.\n\n"
    "Employees who were terminated for cause or who resigned with less than two weeks' notice are "
    "designated as ineligible for rehire."
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 3 -- Code of Conduct
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("3.  Code of Conduct & Ethics")

pdf.section_heading("3.1  Professional Standards")
pdf.body(
    "Orion employees are expected to conduct themselves professionally, honestly, and with integrity "
    "at all times -- both inside and outside the workplace when representing Orion. This means:\n"
)
pdf.bullet([
    "Treating all colleagues, customers, partners, and vendors with respect.",
    "Communicating clearly, honestly, and constructively.",
    "Delivering commitments on time and flagging issues early when timelines are at risk.",
    "Protecting Orion's assets, intellectual property, and confidential information.",
    "Avoiding actions that could embarrass Orion or compromise its reputation.",
])

pdf.section_heading("3.2  Conflicts of Interest")
pdf.body(
    "A conflict of interest exists when an employee's personal interests -- financial, professional, or "
    "relational -- could interfere, or appear to interfere, with their obligations to Orion.\n\n"
    "Employees must disclose any actual or potential conflict of interest to their manager and the "
    "People team immediately upon becoming aware of it. Examples include:"
)
pdf.bullet([
    "Holding a financial interest of more than 1% in a competitor, supplier, or customer.",
    "Serving as a director, officer, or employee of a competitor or supplier.",
    "Having a family member or close personal relationship with someone in a position to influence your compensation, assignment, or promotion.",
    "Accepting a secondary employment arrangement that conflicts with Orion's business interests.",
])
pdf.body(
    "Disclosure does not automatically create a problem -- Orion will work with employees to manage "
    "conflicts appropriately. Failure to disclose a conflict may result in disciplinary action up to "
    "and including termination."
)

pdf.section_heading("3.3  Gifts & Entertainment")
pdf.body(
    "Employees may accept gifts or entertainment from vendors, customers, or business partners only "
    "when all of the following conditions are met:"
)
pdf.bullet([
    "The gift or entertainment has a fair market value of USD $75 or less.",
    "It would not be viewed as an attempt to improperly influence a business decision.",
    "It complies with applicable laws and the recipient's own company policies.",
    "It is not cash or a cash equivalent (gift cards, vouchers, etc.).",
])
pdf.body(
    "Gifts exceeding $75 in value must be declined or, if declining would cause offence, reported to "
    "the People team within five business days. During procurement processes, no gifts of any value "
    "may be accepted from participating vendors."
)

pdf.section_heading("3.4  Confidentiality & Intellectual Property")
pdf.body(
    "Employees have access to confidential information about Orion, its customers, and its business "
    "partners. This includes source code, product roadmaps, financial data, personnel information, "
    "customer data, trade secrets, and business strategies.\n\n"
    "Employees must:\n"
)
pdf.bullet([
    "Not share confidential information with anyone outside Orion without authorisation.",
    "Store and transmit confidential data only using Orion-approved, encrypted channels.",
    "Return or destroy confidential materials upon termination of employment.",
    "Promptly report any actual or suspected breach of confidential information.",
])
pdf.body(
    "All work product created by an employee in the course of their employment belongs to Orion. "
    "Employees must sign Orion's Proprietary Information and Inventions Agreement (PIIA) as a "
    "condition of employment."
)

pdf.section_heading("3.5  Social Media Policy")
pdf.body(
    "Orion respects employees' rights to participate in personal social media activity. However, "
    "when posting online in any capacity that references Orion, employees must:\n"
)
pdf.bullet([
    "Clearly identify that their opinions are personal and do not represent Orion's views.",
    "Not disclose confidential or proprietary information.",
    "Not make false or misleading statements about Orion, its products, employees, or competitors.",
    "Not engage in harassment, hate speech, or content that violates Orion's anti-harassment policy.",
    "Follow all applicable laws regarding securities (no material non-public information).",
])
pdf.body(
    "Employees who are authorised to post on Orion's official social media channels must follow the "
    "Social Media Brand Guidelines available on the People Portal."
)

pdf.section_heading("3.6  Reporting Ethics Concerns")
pdf.body(
    "Orion maintains an anonymous Ethics Hotline operated by a third-party provider. Employees may "
    "report concerns about ethics violations, fraud, financial misconduct, or any other policy "
    "violation without fear of retaliation.\n\n"
    "Ethics Hotline: 1-800-ORN-ETHI (1-800-676-3844)\n"
    "Online: oriontech.ethicspoint.com\n\n"
    "All reports are investigated by the Legal and People teams. Retaliation against any employee "
    "who makes a good-faith report is strictly prohibited and is itself grounds for termination."
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 4 -- Work Hours, Attendance & Remote Work
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("4.  Work Hours, Attendance & Remote Work")

pdf.section_heading("4.1  Standard Work Hours")
pdf.body(
    "Orion's standard work week is 40 hours, Monday through Friday. Core hours -- when all employees "
    "are expected to be available for meetings and collaboration -- are 10:00 AM to 3:00 PM in the "
    "employee's local time zone.\n\n"
    "Exempt employees (salaried) are expected to work the hours necessary to fulfil their job "
    "responsibilities. Non-exempt employees (hourly) must record all hours worked accurately in "
    "Orion's time-tracking system, WorkDay, and must obtain manager approval before working overtime."
)

pdf.section_heading("4.2  Flexible Work Arrangements")
pdf.body(
    "Orion supports flexible scheduling where role requirements permit. Employees may request:"
)
pdf.bullet([
    "Adjusted start/end times (e.g., 7:00 AM - 3:00 PM instead of 9:00 AM - 5:00 PM).",
    "Compressed work weeks (e.g., four 10-hour days).",
    "Part-time schedules.",
])
pdf.body(
    "Requests must be submitted to the employee's manager and approved by the People team. Flexible "
    "arrangements are subject to business needs and may be modified or revoked with two weeks' notice."
)

pdf.section_heading("4.3  Remote Work Policy")
pdf.body(
    "Orion operates as a distributed-first company. Employees may work remotely by default, provided "
    "they meet the following requirements:"
)
pdf.bullet([
    "Maintain a reliable internet connection (minimum 50 Mbps download / 10 Mbps upload).",
    "Work from a private, secure location -- not a public café or shared coworking space -- when handling sensitive data.",
    "Be available during core hours (10:00 AM - 3:00 PM local time).",
    "Attend in-person team gatherings (typically quarterly; travel covered by Orion).",
    "Use Orion-approved, encrypted VPN when accessing internal systems.",
])

pdf.sub_heading("Home Office Stipend")
pdf.body(
    "Full-time employees receive a one-time home office setup stipend of $1,500 upon joining and an "
    "annual equipment refresh allowance of $500 per year. Receipts must be submitted through Concur "
    "within 60 days of purchase. Laptops and other Orion-owned equipment remain company property and "
    "must be returned upon termination."
)

pdf.sub_heading("International Remote Work")
pdf.body(
    "Working from a country other than your country of hire for more than 30 consecutive days "
    "requires prior written approval from the People team and Legal. Tax, immigration, and "
    "employment law implications vary significantly by country and must be assessed in advance."
)

pdf.section_heading("4.4  Attendance & Punctuality")
pdf.body(
    "Consistent attendance is critical to team performance. If you are unable to work due to illness "
    "or an emergency, notify your manager as early as possible -- ideally before your scheduled start "
    "time. Absences must be logged in WorkDay within 24 hours.\n\n"
    "Excessive unplanned absences (more than 5 unscheduled days within any rolling 90-day period, "
    "excluding approved leave) will be addressed through the performance management process described "
    "in Section 12."
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 5 -- Compensation & Payroll
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("5.  Compensation & Payroll")

pdf.section_heading("5.1  Pay Philosophy")
pdf.body(
    "Orion's compensation philosophy is to pay at the 65th percentile of the relevant talent market "
    "for each role and level, using data from Radford, Mercer, and Levels.fyi as primary benchmarks. "
    "Total compensation at Orion is composed of:"
)
pdf.bullet([
    "Base salary -- fixed annual amount paid bi-weekly.",
    "Annual performance bonus -- target 10-20% of base salary depending on level (see Section 5.4).",
    "Equity -- Restricted Stock Units (RSUs) granted at hire and at each annual review cycle.",
    "Benefits -- see Section 6 for full details.",
])

pdf.section_heading("5.2  Pay Periods & Direct Deposit")
pdf.body(
    "Employees are paid bi-weekly (every two weeks) on Fridays, for the two-week pay period ending "
    "the preceding Saturday. When a payday falls on a public holiday, payment is made on the preceding "
    "business day.\n\n"
    "Direct deposit is required for all employees. Banking details are entered through WorkDay during "
    "onboarding. Changes to banking information must be submitted through WorkDay at least five "
    "business days before the next pay date."
)

pdf.section_heading("5.3  Overtime (Non-Exempt Employees)")
pdf.body(
    "Non-exempt employees will be paid overtime at 1.5× their regular hourly rate for all hours "
    "worked in excess of 40 hours in a single work week. In states that mandate daily overtime "
    "(e.g., California), applicable state law will apply.\n\n"
    "All overtime must be approved in advance by the employee's manager. Unauthorised overtime "
    "will still be compensated but may result in disciplinary action."
)

pdf.section_heading("5.4  Annual Performance Bonus")
pdf.body(
    "Orion's annual performance bonus is paid once per year, in March, based on performance in the "
    "prior calendar year. Eligibility requires:"
)
pdf.bullet([
    "Active employment on the date of payment.",
    "A minimum of three months of employment in the performance year.",
    "A performance rating of 'Meets Expectations' or above.",
])
pdf.table(
    ["Level", "Target Bonus (% of Base Salary)", "Maximum Bonus"],
    [
        ["IC1 - IC3 (Associate - Senior)",  "10%",  "15%"],
        ["IC4 - IC5 (Staff - Principal)",   "15%",  "22%"],
        ["IC6+ / Manager - Director",       "20%",  "30%"],
        ["VP and above",                    "30%",  "50%"],
    ],
    col_widths=[75, 75, 40],
)

pdf.section_heading("5.5  Equity -- Restricted Stock Units (RSUs)")
pdf.body(
    "RSUs are granted to employees as part of their total compensation package. Standard vesting "
    "schedule is 4 years with a 1-year cliff: 25% vests after 12 months, then 1/48 per month for "
    "the remaining 36 months.\n\n"
    "RSU grants are subject to approval by the Board of Directors Compensation Committee. Tax "
    "withholding on RSU vesting is handled automatically by Orion's equity administrator, Carta."
)

pdf.section_heading("5.6  Expense Reimbursement")
pdf.body(
    "Orion reimburses employees for reasonable and necessary business expenses incurred in the "
    "performance of their duties. All expenses must be:"
)
pdf.bullet([
    "Submitted through Concur within 30 days of the expense date.",
    "Accompanied by an itemised receipt for any expense over $25.",
    "Approved by the employee's manager before submission where possible.",
])
pdf.body(
    "Expenses over $500 require VP-level approval. Personal expenses, alcohol (unless part of a "
    "pre-approved client entertainment event), fines, and upgrades beyond economy class for flights "
    "under 5 hours are not reimbursable."
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 6 -- Benefits
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("6.  Employee Benefits")

pdf.info_box(
    "Benefits Eligibility",
    "All full-time regular employees are eligible for Orion's benefits on the first day of the month "
    "following their hire date. Part-time employees working 20+ hours per week are eligible for "
    "pro-rated benefits. Benefit details are available on the People Portal at people.oriontech.io."
)

pdf.section_heading("6.1  Health Insurance")
pdf.body(
    "Orion offers three health plan tiers through Cigna, allowing employees to choose the level of "
    "coverage that best suits their needs:"
)
pdf.table(
    ["Plan", "Deductible (Individual)", "Deductible (Family)", "Orion Pays", "Employee Pays"],
    [
        ["Orion Select (PPO)",   "$500",    "$1,000",  "90%",  "10%"],
        ["Orion Choice (PPO)",   "$1,500",  "$3,000",  "80%",  "20%"],
        ["Orion HSA (HDHP)",     "$2,800",  "$5,600",  "70%",  "30%"],
    ],
    col_widths=[42, 38, 35, 37, 38],
)
pdf.body(
    "Orion contributes $1,200/year (individual) or $2,400/year (family) to the Health Savings Account "
    "of employees enrolled in the Orion HSA plan.\n\n"
    "Employees may add dependents (spouse, domestic partner, children up to age 26) to their plan "
    "during open enrollment or within 30 days of a qualifying life event."
)

pdf.section_heading("6.2  Dental & Vision Insurance")
pdf.body(
    "Orion provides dental insurance through Delta Dental and vision insurance through VSP, both "
    "at 100% company-paid premium for the employee. Dependent coverage is available at the "
    "employee's expense.\n\n"
)
pdf.table(
    ["Coverage", "In-Network Benefit"],
    [
        ["Preventive dental (cleanings, X-rays)",  "100% covered"],
        ["Basic dental (fillings, extractions)",    "80% after deductible"],
        ["Major dental (crowns, root canals)",      "50% after deductible"],
        ["Orthodontia (adults & children)",         "50%, $2,000 lifetime max"],
        ["Vision exam",                             "$10 copay, once per year"],
        ["Frames or contact lenses",                "$200 allowance per year"],
    ],
    col_widths=[110, 80],
)

pdf.section_heading("6.3  Life & Disability Insurance")
pdf.bullet([
    "Basic Life Insurance: 2× base salary, company-paid, up to $500,000.",
    "Supplemental Life Insurance: up to 8× base salary, employee-paid at group rates.",
    "Short-Term Disability (STD): 60% of base salary, up to $2,500/week, for up to 12 weeks.",
    "Long-Term Disability (LTD): 60% of base salary, up to $10,000/month, after a 90-day elimination period.",
])

pdf.section_heading("6.4  401(k) Retirement Plan")
pdf.body(
    "Orion offers a 401(k) plan through Fidelity. Employees are eligible to contribute on their "
    "first day of employment and are auto-enrolled at 6% of salary (employees may opt out or "
    "adjust this rate at any time).\n\n"
    "Orion matches 100% of employee contributions up to 5% of base salary. Employer match vests "
    "over 3 years: 33% after year 1, 67% after year 2, 100% after year 3.\n\n"
    "Employees may contribute up to the IRS annual limit ($23,000 for 2025; $30,500 for employees "
    "age 50 and above)."
)

pdf.section_heading("6.5  Employee Assistance Programme (EAP)")
pdf.body(
    "All employees and their household members have access to Orion's Employee Assistance Programme, "
    "provided through Lyra Health. EAP services are confidential and free of charge and include:\n"
)
pdf.bullet([
    "Up to 25 therapy or counselling sessions per year.",
    "Financial planning and debt counselling.",
    "Legal consultation (up to 60 minutes per matter).",
    "Caregiver and eldercare support services.",
    "24/7 crisis line: 1-800-ORN-LYRA",
])

pdf.section_heading("6.6  Additional Benefits")
pdf.table(
    ["Benefit", "Amount / Description"],
    [
        ["Professional Development Stipend",  "$2,000 per year for courses, books, or conferences"],
        ["Home Office Setup (one-time)",       "$1,500 at hire"],
        ["Annual Equipment Refresh",           "$500 per year"],
        ["Wellness Stipend",                   "$600 per year (gym, apps, fitness equipment)"],
        ["Commuter Benefits (FSA)",            "Pre-tax transit/parking up to IRS limit"],
        ["Dependent Care FSA",                 "Up to $5,000 per year pre-tax"],
        ["Orion Gives (charity matching)",     "Up to $1,000 per year matched dollar-for-dollar"],
        ["Employee Referral Bonus",            "$3,000 - $7,500 depending on role level"],
    ],
    col_widths=[80, 110],
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 7 -- Time Off & Leave
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("7.  Time Off & Leave Policies")

pdf.section_heading("7.1  Paid Time Off (PTO)")
pdf.body(
    "Orion provides a flexible PTO policy for all full-time exempt employees, meaning there is no "
    "preset cap on PTO days. Employees are expected to take at least 15 days off per year and are "
    "encouraged to take 20-25 days. PTO must be scheduled with manager approval, taking into account "
    "business needs and team coverage.\n\n"
    "Non-exempt employees accrue PTO at the following rate:"
)
pdf.table(
    ["Years of Service", "Accrual Rate", "Maximum Annual PTO"],
    [
        ["0 - 2 years",  "0.077 hrs/hr worked",  "160 hours (20 days)"],
        ["2 - 5 years",  "0.096 hrs/hr worked",  "200 hours (25 days)"],
        ["5+ years",     "0.115 hrs/hr worked",  "240 hours (30 days)"],
    ],
    col_widths=[63, 63, 64],
)

pdf.section_heading("7.2  Company Holidays")
pdf.body("Orion observes 12 company-wide paid holidays per year:")
pdf.table(
    ["Holiday", "2025 Date"],
    [
        ["New Year's Day",            "January 1"],
        ["Martin Luther King Jr. Day", "January 20"],
        ["Presidents' Day",           "February 17"],
        ["Memorial Day",              "May 26"],
        ["Juneteenth",                "June 19"],
        ["Independence Day",          "July 4"],
        ["Labor Day",                 "September 1"],
        ["Thanksgiving Day",          "November 27"],
        ["Day after Thanksgiving",    "November 28"],
        ["Christmas Eve",             "December 24"],
        ["Christmas Day",             "December 25"],
        ["New Year's Eve",            "December 31"],
    ],
    col_widths=[110, 80],
)
pdf.body(
    "Employees outside the United States observe the statutory public holidays of their country "
    "of employment in place of the US holidays listed above."
)

pdf.section_heading("7.3  Sick Leave")
pdf.body(
    "Full-time employees receive 10 days (80 hours) of paid sick leave per calendar year. Sick "
    "leave may be used for:\n"
)
pdf.bullet([
    "The employee's own physical or mental illness, injury, or medical appointments.",
    "Care of an immediate family member (spouse, child, parent, sibling, grandparent, or domestic partner) who is ill.",
    "Medical appointments that cannot be scheduled outside work hours.",
])
pdf.body(
    "Sick leave does not carry over from year to year and is not paid out upon termination. "
    "For absences of 5 or more consecutive days, a doctor's note is required."
)

pdf.section_heading("7.4  Parental Leave")
pdf.body(
    "Orion provides generous parental leave to support employees growing their families, regardless "
    "of gender, parental role, or method of becoming a parent (birth, adoption, foster placement)."
)
pdf.table(
    ["Leave Type", "Duration", "Pay", "Eligibility"],
    [
        ["Primary Caregiver Leave",  "20 weeks",  "100% of base salary",  "All full-time employees"],
        ["Secondary Caregiver Leave", "8 weeks",  "100% of base salary",  "All full-time employees"],
        ["Adoption / Foster Leave",  "Up to 20 wks", "100% of base salary", "All full-time employees"],
    ],
    col_widths=[50, 30, 50, 60],
)
pdf.body(
    "Parental leave must commence within 12 months of the birth, adoption, or foster placement. "
    "Employees must provide at least 30 days' advance notice where possible. Leave may be taken "
    "consecutively or intermittently with manager agreement."
)

pdf.section_heading("7.5  Bereavement Leave")
pdf.body("Orion provides paid bereavement leave upon the death of a family member or close friend:")
pdf.bullet([
    "Immediate family (spouse, child, parent, sibling, grandparent): 5 paid days.",
    "Extended family (aunt, uncle, cousin, in-law): 3 paid days.",
    "Close friend or non-traditional family relationship: 2 paid days (manager discretion).",
    "Pregnancy loss (employee or partner): 5 paid days.",
])

pdf.section_heading("7.6  Jury Duty & Voting Leave")
pdf.body(
    "Employees summoned for jury duty will receive full pay for up to 3 weeks. For jury service "
    "exceeding 3 weeks, Orion will pay the difference between jury pay and the employee's regular "
    "base salary for up to 6 months.\n\n"
    "Orion provides up to 2 hours of paid leave to vote in any federal, state, or local election "
    "if the employee cannot reasonably vote outside working hours. Employees must notify their "
    "manager at least 2 days in advance."
)

pdf.section_heading("7.7  Unpaid Leaves of Absence")
pdf.body(
    "Employees may request an unpaid personal leave of absence of up to 3 months for personal "
    "or family reasons not covered by other leave policies. Approval is at manager and People "
    "team discretion and depends on business needs. Benefits continue during approved unpaid "
    "leave, though the employee is responsible for paying their share of benefit premiums."
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 8 -- Performance & Development
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("8.  Performance, Growth & Development")

pdf.section_heading("8.1  Performance Review Cycle")
pdf.body(
    "Orion conducts formal performance reviews twice per year:\n"
)
pdf.bullet([
    "Mid-Year Check-In (June): Informal, focused on progress against goals and development needs.",
    "Annual Review (December): Formal, including self-assessment, peer feedback, manager rating, and compensation decisions.",
])
pdf.body(
    "Performance ratings use a 5-point scale:\n"
)
pdf.table(
    ["Rating", "Label", "Description"],
    [
        ["5", "Exceptional",       "Significantly exceeds expectations; transformational impact"],
        ["4", "Exceeds",           "Consistently exceeds expectations in most areas"],
        ["3", "Meets",             "Fully meets expectations; solid, reliable contribution"],
        ["2", "Developing",        "Partially meets expectations; improvement plan in place"],
        ["1", "Below Expectations","Does not meet core expectations; immediate action required"],
    ],
    col_widths=[15, 45, 130],
)

pdf.section_heading("8.2  Goal Setting (OKRs)")
pdf.body(
    "Orion uses Objectives and Key Results (OKRs) for goal setting at all levels. Goals are set "
    "quarterly at company, team, and individual levels and tracked in Lattice.\n\n"
    "Each employee is expected to set 3-5 individual OKRs per quarter in alignment with their "
    "team's objectives. OKRs are graded at the end of each quarter on a 0.0 - 1.0 scale."
)

pdf.section_heading("8.3  Career Levels & Progression")
pdf.body("Orion's engineering career ladder (Individual Contributor track):")
pdf.table(
    ["Level", "Title",                "Typical Experience"],
    [
        ["IC1", "Associate Engineer",  "0-2 years"],
        ["IC2", "Software Engineer",   "2-4 years"],
        ["IC3", "Senior Engineer",     "4-7 years"],
        ["IC4", "Staff Engineer",      "7-12 years"],
        ["IC5", "Principal Engineer",  "12+ years"],
        ["IC6", "Distinguished Eng.",  "Industry recognition"],
    ],
    col_widths=[20, 70, 100],
)
pdf.body(
    "Promotions are decided during the annual review cycle. To be considered, an employee must "
    "have demonstrated sustained performance at the next level for at least two consecutive quarters, "
    "as documented by their manager."
)

pdf.section_heading("8.4  Learning & Development")
pdf.body(
    "Orion invests $2,000 per employee per year in professional development. Approved uses include:"
)
pdf.bullet([
    "Online courses (Coursera, Pluralsight, O'Reilly Learning, etc.).",
    "Industry conferences and workshops (travel and registration covered separately up to $3,000).",
    "Professional certifications (AWS, GCP, CKA, etc.) -- exam fees and one retake covered.",
    "Books, journals, and technical publications.",
])
pdf.body(
    "Requests over $200 must be pre-approved through the People Portal. Orion also offers an "
    "internal learning platform, OrionLearn, with over 2,000 courses available to all employees "
    "at no additional cost."
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 9 -- IT & Security
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("9.  Information Technology & Security")

pdf.section_heading("9.1  Acceptable Use Policy")
pdf.body(
    "Orion provides computing equipment, software, and network access to employees for the purpose "
    "of conducting Orion business. Limited personal use of Orion systems is permitted provided it:"
)
pdf.bullet([
    "Does not interfere with productivity or job performance.",
    "Does not consume excessive bandwidth or storage.",
    "Does not involve illegal activity, adult content, gambling, or cryptocurrency mining.",
    "Does not compromise the security of Orion's systems or data.",
])
pdf.body(
    "Employees should have no expectation of privacy when using Orion-owned devices or networks. "
    "Orion reserves the right to monitor, access, and review all activity on company systems."
)

pdf.section_heading("9.2  Password & Authentication Policy")
pdf.bullet([
    "All accounts must use strong, unique passwords (minimum 16 characters).",
    "Multi-Factor Authentication (MFA) is mandatory for all Orion systems, including email, GitHub, AWS, and the VPN.",
    "Passwords must never be shared, written down, or stored in plain text.",
    "Orion uses 1Password as its corporate password manager -- all employees receive a company account.",
    "SSH key passphrases are required; passwordless SSH keys are prohibited.",
])

pdf.section_heading("9.3  Data Classification & Handling")
pdf.table(
    ["Classification", "Examples", "Handling Requirements"],
    [
        ["Public",       "Marketing materials, press releases",       "No restrictions"],
        ["Internal",     "Company policies, internal docs",           "Orion systems only"],
        ["Confidential", "Customer data, financial data, source code","Encrypted, need-to-know"],
        ["Restricted",   "PII, health data, credentials",            "Encrypted, MFA, logged access"],
    ],
    col_widths=[30, 75, 85],
)

pdf.section_heading("9.4  Device Policy")
pdf.body(
    "Orion provides all employees with a company-owned laptop (MacBook Pro or equivalent). "
    "Use of personal devices to access Orion systems is permitted only via Orion's Mobile Device "
    "Management (MDM) solution, Jamf, with manager approval.\n\n"
    "All Orion devices must:\n"
)
pdf.bullet([
    "Run the latest approved OS version within 30 days of release.",
    "Have full-disk encryption enabled (FileVault on Mac, BitLocker on Windows).",
    "Have the Orion endpoint security agent (CrowdStrike) installed and active.",
    "Never be left unattended in public spaces without being locked.",
])
pdf.body("Lost or stolen devices must be reported to IT Security within 1 hour of discovery.")

pdf.section_heading("9.5  Incident Reporting")
pdf.body(
    "Employees must report any actual or suspected security incident -- including phishing emails, "
    "malware, data exposure, or lost/stolen devices -- to the Information Security team immediately:\n\n"
    "Email: security@oriontech.io\n"
    "Slack: #security-incidents (24/7 monitored)\n"
    "Phone: +1 (512) 400-7200 ext. 911 (after hours)\n\n"
    "Prompt reporting reduces harm and is a condition of employment. Failure to report a known "
    "security incident may result in disciplinary action."
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 10 -- Workplace Health & Safety
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("10.  Workplace Health & Safety")

pdf.section_heading("10.1  Commitment to Safety")
pdf.body(
    "Orion is committed to providing a safe and healthy work environment for all employees, "
    "contractors, and visitors. We comply with all applicable Occupational Safety and Health "
    "Administration (OSHA) regulations and maintain a comprehensive Injury and Illness Prevention "
    "Programme (IIPP)."
)

pdf.section_heading("10.2  Reporting Injuries & Incidents")
pdf.body(
    "Any work-related injury, illness, or unsafe condition must be reported to the employee's "
    "manager and the Facilities team within 24 hours of occurrence. For injuries requiring "
    "immediate medical attention, call 911 first.\n\n"
    "Workers' Compensation insurance covers all work-related injuries and illnesses. Employees "
    "must file a claim through HR within 24 hours of an incident to ensure coverage. Failure "
    "to report a workplace injury promptly may affect eligibility for Workers' Compensation benefits."
)

pdf.section_heading("10.3  Drug & Alcohol Policy")
pdf.body(
    "Orion maintains a drug-free workplace. Employees are prohibited from:\n"
)
pdf.bullet([
    "Reporting to work while impaired by alcohol, illegal drugs, or any controlled substance.",
    "Using, possessing, distributing, or selling illegal drugs on company premises or during company activities.",
    "Consuming alcohol during work hours, except at company-sponsored events where alcohol is served.",
])
pdf.body(
    "Violation of this policy may result in immediate termination. Employees struggling with "
    "substance use are encouraged to seek confidential support through the EAP (Section 6.5) "
    "before performance or conduct issues arise."
)

pdf.section_heading("10.4  Emergency Procedures")
pdf.body(
    "Emergency evacuation maps are posted at all Orion office locations. Employees should "
    "familiarise themselves with the nearest exits and assembly points on their first day.\n\n"
    "In the event of a fire, active threat, or other emergency:\n"
)
pdf.bullet([
    "Evacuate the building calmly using the nearest stairwell -- do not use lifts.",
    "Proceed to the designated assembly point for your floor.",
    "Do not re-enter the building until cleared by emergency services.",
    "Account for your team members and report any missing persons to the floor warden.",
])

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 11 -- Anti-Harassment & Non-Discrimination
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("11.  Anti-Harassment & Non-Discrimination")

pdf.section_heading("11.1  Policy Statement")
pdf.body(
    "Orion Technologies is committed to maintaining a workplace free from all forms of harassment, "
    "discrimination, and retaliation. This policy applies to all employees, contractors, interns, "
    "and vendors and covers conduct that occurs in the workplace, at company-sponsored events, and "
    "in work-related communications (email, Slack, video calls).\n\n"
    "Harassment is any unwelcome conduct based on a protected characteristic (race, sex, religion, "
    "national origin, age, disability, sexual orientation, gender identity, or any other legally "
    "protected status) that creates a hostile, intimidating, or offensive work environment, or "
    "that results in an adverse employment decision.\n\n"
    "Sexual harassment includes unwelcome sexual advances, requests for sexual favours, and other "
    "verbal or physical conduct of a sexual nature. It includes quid pro quo harassment (submission "
    "to sexual conduct as a condition of employment) and hostile environment harassment."
)

pdf.section_heading("11.2  Reporting Procedure")
pdf.body(
    "Any employee who believes they have experienced or witnessed harassment or discrimination "
    "should report it as soon as possible using one of the following channels:\n"
)
pdf.bullet([
    "Direct report to your manager (if the manager is not the subject of the complaint).",
    "Report to any member of the People team.",
    "Anonymous report via the Ethics Hotline: 1-800-676-3844 or oriontech.ethicspoint.com.",
    "Email to: hr-confidential@oriontech.io (reviewed only by the CPO and Legal).",
])
pdf.body(
    "Reports may be made verbally or in writing. Employees are not required to confront the "
    "person whose behaviour they are reporting before making a formal complaint."
)

pdf.section_heading("11.3  Investigation Process")
pdf.body(
    "All reports of harassment or discrimination will be:\n"
)
pdf.bullet([
    "Acknowledged within 1 business day of receipt.",
    "Investigated promptly, thoroughly, and impartially by the People team and/or Legal.",
    "Kept as confidential as possible, limited to those with a need to know.",
    "Resolved with appropriate corrective action if the complaint is substantiated.",
])
pdf.body(
    "Both the reporting employee and the subject of the complaint will be notified of the outcome "
    "to the extent permitted by confidentiality obligations."
)

pdf.section_heading("11.4  Non-Retaliation")
pdf.body(
    "Orion strictly prohibits retaliation against any employee who makes a good-faith report of "
    "harassment or discrimination, or who participates in an investigation. Retaliation includes "
    "termination, demotion, schedule changes, exclusion, or any other adverse action.\n\n"
    "Retaliation is itself grounds for disciplinary action up to and including termination, "
    "regardless of the outcome of the underlying complaint."
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 12 -- Disciplinary Procedures
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("12.  Disciplinary Procedures")

pdf.section_heading("12.1  Progressive Discipline")
pdf.body(
    "When an employee's performance or conduct does not meet Orion's standards, we generally follow "
    "a progressive discipline process. The goal is corrective, not punitive -- to give employees a "
    "clear opportunity to improve before more serious action is taken.\n\n"
    "The typical steps are:\n"
)
pdf.bullet([
    "Step 1 -- Verbal Warning: Manager discusses the issue, expectations, and required improvement. Documented in the employee's file.",
    "Step 2 -- Written Warning: Formal written notice describing the issue, prior discussions, required changes, and consequences of continued non-compliance.",
    "Step 3 -- Performance Improvement Plan (PIP): 30-90 day structured plan with specific, measurable goals and weekly check-ins.",
    "Step 4 -- Final Written Warning or Suspension: Last formal notice before termination, or unpaid suspension pending investigation.",
    "Step 5 -- Termination of Employment.",
])
pdf.body(
    "Orion reserves the right to skip steps or apply any step at any time, depending on the "
    "severity of the conduct. Progressive discipline does not alter the at-will nature of employment."
)

pdf.section_heading("12.2  Grounds for Immediate Termination")
pdf.body(
    "Certain conduct is so serious that it warrants immediate termination without prior warning, "
    "regardless of prior performance history. Examples include (but are not limited to):\n"
)
pdf.bullet([
    "Theft, fraud, or deliberate misappropriation of company or customer assets.",
    "Physical violence or credible threats of violence against any person.",
    "Harassment resulting in a hostile work environment after investigation.",
    "Intentional breach of data security or confidentiality obligations.",
    "Falsification of employment records, time records, or expense reports.",
    "Possession or use of illegal drugs on company premises.",
    "Serious violation of Orion's Code of Conduct.",
    "Conduct that causes material harm to Orion's reputation or financial standing.",
])

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 13 -- Separation & Offboarding
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("13.  Separation & Offboarding")

pdf.section_heading("13.1  Voluntary Resignation")
pdf.body(
    "Employees who wish to resign should notify their manager in writing as early as possible. "
    "The expected notice period by level is:\n"
)
pdf.table(
    ["Level", "Notice Period"],
    [
        ["IC1 - IC3",               "2 weeks"],
        ["IC4 - IC5 / Manager",     "4 weeks"],
        ["Director and above",      "6 weeks"],
    ],
    col_widths=[95, 95],
)
pdf.body(
    "Orion may, at its discretion, accept shorter notice, place the employee on garden leave "
    "for the notice period, or waive the notice period entirely. The employee's last day will "
    "be confirmed in writing by the People team."
)

pdf.section_heading("13.2  Involuntary Termination")
pdf.body(
    "Orion will communicate termination decisions directly and respectfully. The People team and "
    "the employee's manager will be present. The employee will be informed of:\n"
)
pdf.bullet([
    "The effective date of termination.",
    "Severance entitlements, if any (see Section 13.3).",
    "The process for returning company property.",
    "Continuation of benefits (COBRA, RSU vesting, final pay).",
    "Any post-employment obligations (non-solicitation, confidentiality).",
])

pdf.section_heading("13.3  Severance")
pdf.body(
    "Severance is not guaranteed and is provided at Orion's discretion based on circumstances. "
    "When offered, standard severance guidelines are:\n"
)
pdf.table(
    ["Years of Service",  "Severance (Weeks of Base Pay)"],
    [
        ["Less than 1 year",  "2 weeks"],
        ["1 - 3 years",       "1 week per year of service (min. 4 weeks)"],
        ["3 - 7 years",       "1.5 weeks per year of service"],
        ["7+ years",          "2 weeks per year of service (max. 26 weeks)"],
    ],
    col_widths=[95, 95],
)
pdf.body(
    "Severance is contingent on the employee signing a separation agreement and general release "
    "of claims. Severance is not offered in cases of termination for cause."
)

pdf.section_heading("13.4  Final Pay")
pdf.body(
    "Final pay, including all earned but unpaid wages and accrued but unused PTO (for non-exempt "
    "employees), will be paid in accordance with applicable state law -- typically on the last day "
    "of employment (California, Colorado) or the next regular pay date (most other states).\n\n"
    "Exempt employees are not entitled to PTO payout unless required by state law or specified in "
    "the separation agreement."
)

pdf.section_heading("13.5  Return of Company Property")
pdf.body(
    "On or before the last day of employment, departing employees must return all Orion property, "
    "including:\n"
)
pdf.bullet([
    "Laptop and all peripherals (charger, monitors, keyboard, mouse).",
    "Access badges, keys, and parking passes.",
    "Any confidential documents, printed materials, or data storage devices.",
    "Corporate credit cards.",
])
pdf.body(
    "Employees who fail to return company property may be invoiced for the replacement cost. "
    "All access to Orion systems is revoked on the final day of employment."
)

pdf.section_heading("13.6  References & Employment Verification")
pdf.body(
    "Orion's policy is to confirm employment dates and job title only when responding to "
    "external reference requests. Any employee or manager who provides a reference beyond these "
    "facts does so in a personal capacity and must not represent themselves as speaking on "
    "behalf of Orion.\n\n"
    "Employment verification requests should be directed to: hr@oriontech.io"
)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 14 -- Acknowledgment
# ═══════════════════════════════════════════════════════════════════════════
pdf.new_chapter("14.  Acknowledgment of Receipt")

pdf.body(
    "By signing below, I acknowledge that I have received, read, and understood the Orion "
    "Technologies Employee Handbook (Version 4.2, effective January 1, 2025). I understand that:\n"
)
pdf.bullet([
    "This handbook describes Orion's policies, expectations, and benefits as of the effective date.",
    "The handbook is not an employment contract and does not alter the at-will nature of my employment.",
    "Orion may update, modify, or revoke any policy in this handbook at any time.",
    "It is my responsibility to read and comply with all policies contained herein.",
    "Failure to comply with these policies may result in disciplinary action up to and including termination.",
])

pdf.ln(12)
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(*BLACK)

fields = [
    ("Full Legal Name (Print)", ""),
    ("Job Title", ""),
    ("Department", ""),
    ("Employee ID", ""),
    ("Date of Hire", ""),
    ("Signature", ""),
    ("Date Signed", ""),
]

for label, _ in fields:
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(70, 7, label + ":", ln=False)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.3)
    x = pdf.get_x()
    y = pdf.get_y() + 6
    pdf.line(x, y, 200, y)
    pdf.ln(10)

pdf.ln(5)
pdf.info_box(
    "Submit this form",
    "Please return this signed acknowledgment to the People team at hr@oriontech.io or deposit "
    "it in the HR drop-box on the 9th floor within 5 business days of your start date. "
    "A digital version is available on the People Portal at people.oriontech.io."
)

# ── Output ──────────────────────────────────────────────────────────────────
output_path = "/Users/KC/Documents/rag-demo/docs/sample-data/orion-technologies-employee-handbook.pdf"
pdf.output(output_path)
print(f"Generated: {output_path}  ({pdf.page_no()} pages)")
