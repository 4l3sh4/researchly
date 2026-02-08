from __future__ import annotations

"""
seed_demo_data.py

Seeds realistic demo data for the "Researchly" Flask app (SQLite).
- Resets DB (drop_all/create_all) for repeatable testing.
- Creates users across roles + account states (PENDING / ACTIVE / DEACTIVATED).
- Creates departments + HOD mapping.
- Creates grant schemes (OPEN / CLOSED / DRAFT).
- Creates proposals across pipeline states so admin dashboards & workflows can be tested.
- Creates reviewer assignments, reviews, HoD endorsements, final decisions, projects, funding allocations.
- Creates proposal attachments (with small dummy files in static/uploads).
- Creates progress reports, notifications, and activity logs.

Run:
  python seed_demo_data.py

Then login:
  Admin:       admin@researchly.demo / 1234
  Researcher:  aisyah.rahman@researchly.demo / demo123
  Reviewer:    nur.farhana@researchly.demo / demo123
  HOD:         prof.hakim@researchly.demo / demo123
"""

from datetime import datetime, timezone, date, timedelta
import os
import uuid
import random

from main import (
    app, db, bcrypt,

    # Core user tables
    User, UserProfile,
    Admin, HOD, Reviewer, Researcher,
    BankAccount,

    # Domain tables
    Department, GrantScheme, Proposal,
    ProposalAttachment,
    ReviewersAssignment, Review,
    HODEndorsement, FinalDecision,
    Project, FundingAllocation,
    ProgressReport,
    Notification,
    ActivityLog,
)

# -------------------------
# Utilities
# -------------------------

RND = random.Random(20260208)  # deterministic "legit" demo data

def uid() -> str:
    return str(uuid.uuid4())

def hash_pw(pw: str) -> str:
    return bcrypt.generate_password_hash(pw).decode("utf-8")

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def dt_utc(days_ago: int = 0, minutes_ago: int = 0) -> datetime:
    return now_utc() - timedelta(days=days_ago, minutes=minutes_ago)

def ensure_upload_folder() -> str:
    folder = app.config.get("UPLOAD_FOLDER")
    if not folder:
        # fallback (should match main.py)
        folder = os.path.join(app.root_path, "static", "uploads")
    os.makedirs(folder, exist_ok=True)
    return folder

def create_dummy_upload(filename: str, text: str) -> str:
    """Creates a tiny dummy file in static/uploads to match ProposalAttachment.stored_filename."""
    folder = ensure_upload_folder()
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(text.encode("utf-8"))
    return filename

def log_activity(message: str, action: str = "SEED", proposal_id: str | None = None, actor_user_id: str | None = None, created_at: datetime | None = None):
    db.session.add(ActivityLog(
        activity_id=uid(),
        created_at=created_at or now_utc(),
        actor_user_id=actor_user_id,
        proposal_id=proposal_id,
        action=action,
        message=message,
    ))

def create_notif(user_id: str, message: str, notif_type: str = "INFO", is_read: bool = False, created_at: datetime | None = None):
    db.session.add(Notification(
        notification_id=uid(),
        user_id=user_id,
        message=message[:100],  # model limits message to 100 chars
        notif_type=notif_type,
        created_at=created_at or now_utc(),
        is_read=is_read,
    ))

def get_or_create_user(email: str, full_name: str, password_plain: str):
    u = User.query.filter_by(email=email).first()
    if u:
        return u
    u = User(id=uid(), full_name=full_name, email=email, password=hash_pw(password_plain))
    db.session.add(u)
    db.session.commit()
    return u

def upsert_profile(
    user_id: str,
    role: str,
    account_status: str,
    *,
    contact_number: str | None = None,
    address: str | None = None,
    emergency_name: str | None = None,
    emergency_number: str | None = None,
    department_name: str | None = None,
    expertise_tags: str | None = None,
    profile_picture: str | None = None,
):
    prof = UserProfile.query.filter_by(user_id=user_id).first()
    if not prof:
        prof = UserProfile(user_id=user_id)
        db.session.add(prof)

    prof.role = role.upper()
    prof.account_status = account_status.upper()

    # Make profiles "complete" so you can access dashboards without being blocked.
    prof.contact_number = contact_number or prof.contact_number or f"01{RND.randint(0,9)}-{RND.randint(1000000,9999999)}"
    prof.address = address or prof.address or "No. 12, Jalan Teknologi 5, 63000 Cyberjaya, Selangor"
    prof.emergency_contact_name = emergency_name or prof.emergency_contact_name or "Siti Rahman"
    prof.emergency_contact_number = emergency_number or prof.emergency_contact_number or f"01{RND.randint(0,9)}-{RND.randint(1000000,9999999)}"
    prof.department_name = department_name  # can be None for ADMIN
    prof.expertise_tags = expertise_tags
    prof.profile_picture = profile_picture

    db.session.commit()
    return prof

def ensure_role_row(role: str, user_id: str):
    role = role.upper()
    if role == "ADMIN":
        row = Admin.query.filter_by(user_id=user_id).first()
        if not row:
            row = Admin(admin_id=uid(), user_id=user_id)
            db.session.add(row); db.session.commit()
        return row
    if role == "HOD":
        row = HOD.query.filter_by(user_id=user_id).first()
        if not row:
            row = HOD(hod_id=uid(), user_id=user_id)
            db.session.add(row); db.session.commit()
        return row
    if role == "REVIEWER":
        row = Reviewer.query.filter_by(user_id=user_id).first()
        if not row:
            row = Reviewer(reviewer_id=uid(), user_id=user_id)
            db.session.add(row); db.session.commit()
        return row
    if role == "RESEARCHER":
        row = Researcher.query.filter_by(user_id=user_id).first()
        if not row:
            row = Researcher(researcher_id=uid(), user_id=user_id)
            db.session.add(row); db.session.commit()
        return row
    raise ValueError(f"Unknown role: {role}")

def get_or_create_bank(account_no: str, bank_name: str):
    b = BankAccount.query.filter_by(bank_account_number=account_no).first()
    if b:
        b.bank_name = bank_name
        db.session.commit()
        return b
    b = BankAccount(bank_account_number=account_no, bank_name=bank_name)
    db.session.add(b); db.session.commit()
    return b

def get_or_create_department(dept_name: str, dept_desc: str, hod_id: str):
    dept = Department.query.filter_by(department_name=dept_name).first()
    if dept:
        dept.hod_id = hod_id
        dept.department_description = dept_desc
        db.session.commit()
        return dept
    dept = Department(
        department_id=uid(),
        hod_id=hod_id,
        department_name=dept_name,
        department_description=dept_desc,
    )
    db.session.add(dept); db.session.commit()
    return dept

def create_scheme(admin_id: str, dept: Department, *, status: str):
    """status: OPEN / CLOSED / DRAFT"""
    status = status.upper()
    title = {
        "OPEN": "Open Call",
        "CLOSED": "Closed Call",
        "DRAFT": "Draft Scheme",
    }.get(status, status)

    desc = f"{dept.department_name} Research Grant — {title}"
    scheme = GrantScheme.query.filter_by(description=desc).first()
    if scheme:
        scheme.scheme_status = status
        db.session.commit()
        return scheme

    # Make date ranges "feel real"
    open_date = date.today() - timedelta(days=7)
    close_date = date.today() + timedelta(days=21)
    if status == "CLOSED":
        open_date = date.today() - timedelta(days=60)
        close_date = date.today() - timedelta(days=3)
    if status == "DRAFT":
        open_date = date.today() + timedelta(days=7)
        close_date = date.today() + timedelta(days=45)

    scheme = GrantScheme(
        scheme_id=uid(),
        admin_id=admin_id,
        department_id=dept.department_id,
        description=desc,
        eligibiliity="Academic staff / postgraduate researchers with departmental support",
        open_date=open_date,
        close_date=close_date,
        max_budget=RND.choice([30000, 50000, 75000, 100000]),
        project_duration_limit=RND.choice([6, 12, 18, 24]),
        required_documents="Proposal, Budget Breakdown, CV, Supporting Letter",
        reporting_requirements="Mid-term progress report and final report within 30 days of completion",
        scheme_status=status,
    )
    db.session.add(scheme); db.session.commit()
    return scheme

def create_proposal(
    scheme_id: str,
    researcher_id: str,
    title: str,
    *,
    status: str,
    submitted_at: datetime | None = None,
    requested_budget: int = 25000,
):
    p = Proposal.query.filter_by(project_title=title).first()
    if p:
        return p

    # Slightly varied content so UI feels real
    abstracts = [
        "This study investigates practical approaches to improve reliability and transparency in grant workflows.",
        "The project evaluates scalable methods for secure data handling with measurable outcomes for stakeholders.",
        "We propose a lightweight framework that balances cost, impact, and institutional constraints.",
    ]
    methods = [
        "Literature review, requirements analysis, prototype implementation, and evaluation using predefined metrics.",
        "Mixed-method approach: quantitative benchmarking plus qualitative interviews with domain experts.",
        "Iterative development with pilot deployment, feedback loops, and controlled testing.",
    ]

    p = Proposal(
        proposal_id=uid(),
        scheme_id=scheme_id,
        researcher_id=researcher_id,
        project_title=title,
        abstract=RND.choice(abstracts),
        methodology=RND.choice(methods),
        requested_budget=requested_budget,
        expertise_needed=RND.choice([
            "Data analytics, reporting, stakeholder interviews",
            "Cybersecurity, risk assessment, secure storage",
            "UI/UX, survey design, evaluation methodology",
            "None (small internal study)",
        ]),
        submission_date=submitted_at or now_utc(),
        proposal_status=status,
    )
    db.session.add(p); db.session.commit()
    return p

def clear_workflow(proposal_id: str):
    Review.query.filter_by(proposal_id=proposal_id).delete()
    ReviewersAssignment.query.filter_by(proposal_id=proposal_id).delete()
    HODEndorsement.query.filter_by(proposal_id=proposal_id).delete()
    FinalDecision.query.filter_by(proposal_id=proposal_id).delete()

    proj = Project.query.filter_by(proposal_id=proposal_id).first()
    if proj:
        FundingAllocation.query.filter_by(project_id=proj.project_id).delete()
        ProgressReport.query.filter_by(project_id=proj.project_id).delete()
        db.session.delete(proj)

    db.session.commit()

def add_attachment(proposal_id: str, original_name: str, kind: str):
    # Use deterministic filename so it doesn't grow endlessly across runs.
    stored_name = f"{proposal_id[:8]}_{kind}.txt"
    create_dummy_upload(stored_name, f"Dummy {kind} for proposal {proposal_id}\nGenerated by seed_demo_data.py\n")
    db.session.add(ProposalAttachment(
        attachment_id=uid(),
        proposal_id=proposal_id,
        stored_filename=stored_name,
        original_filename=original_name,
        uploaded_at=now_utc(),
    ))
    db.session.commit()

def assign_reviewers(proposal_id: str, reviewers: list[Reviewer], count: int = 2):
    for rv in reviewers[:count]:
        if not ReviewersAssignment.query.filter_by(proposal_id=proposal_id, reviewer_id=rv.reviewer_id).first():
            db.session.add(ReviewersAssignment(
                assignment_id=uid(),
                proposal_id=proposal_id,
                reviewer_id=rv.reviewer_id,
                assigned_date=now_utc(),
                assignment_status="ASSIGNED",
            ))
    db.session.commit()

def add_reviews(proposal_id: str, reviewers: list[Reviewer], count: int = 2, *, approve_ratio: float = 1.0):
    assign_reviewers(proposal_id, reviewers, count=count)
    for i, rv in enumerate(reviewers[:count]):
        if Review.query.filter_by(proposal_id=proposal_id, reviewer_id=rv.reviewer_id).first():
            continue
        rec = "APPROVE" if (i / max(1, count-1)) <= approve_ratio else "REJECT"
        db.session.add(Review(
            review_id=uid(),
            proposal_id=proposal_id,
            reviewer_id=rv.reviewer_id,
            review_date=now_utc(),
            recommendation=rec,
            feedback=(
                "Strong alignment with scheme objectives; please clarify timeline and evaluation plan."
                if rec == "APPROVE" else
                "Scope is unclear; revise research questions and provide clearer budget justification."
            ),
        ))
    db.session.commit()

def add_hod_endorsement(proposal_id: str, hod_id: str, decision: str, remarks: str):
    if not HODEndorsement.query.filter_by(proposal_id=proposal_id).first():
        db.session.add(HODEndorsement(
            hod_endorsement_id=uid(),
            hod_id=hod_id,
            proposal_id=proposal_id,
            decision=decision,
            decision_date=now_utc(),
            remarks=remarks,
        ))
    db.session.commit()

def set_final_decision(proposal_id: str, admin_id: str, decision: str):
    fd = FinalDecision.query.filter_by(proposal_id=proposal_id).first()
    if not fd:
        db.session.add(FinalDecision(
            final_decision_id=uid(),
            proposal_id=proposal_id,
            admin_id=admin_id,
            decision=decision,
            decision_date=now_utc(),
        ))
    else:
        fd.decision = decision
        fd.decision_date = now_utc()

    # Keep Proposal.proposal_status consistent with "end-state" usage in compute_proposal_display_status()
    p = db.session.get(Proposal, proposal_id)
    if p and decision.upper() == "REJECTED":
        p.proposal_status = "REJECTED"

    db.session.commit()

def create_project_and_funding(proposal: Proposal, admin_id: str, *, allocation_status: str):
    """
    allocation_status: DRAFT / CONFIRMED
    - DRAFT     => display should stay "Pending Funding"
    - CONFIRMED => display should be "Funded"
    """
    proj = Project.query.filter_by(proposal_id=proposal.proposal_id).first()
    if not proj:
        proj = Project(
            project_id=uid(),
            proposal_id=proposal.proposal_id,
            researcher_id=proposal.researcher_id,
            scheme_id=proposal.scheme_id,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() + timedelta(days=170),
            project_status="ONGOING" if allocation_status.upper() == "CONFIRMED" else "DRAFT",
        )
        db.session.add(proj); db.session.commit()

    total = int(proposal.requested_budget)
    equipment = int(total * 0.35)
    materials = int(total * 0.25)
    travel = int(total * 0.20)
    other = total - (equipment + materials + travel)

    alloc = FundingAllocation.query.filter_by(project_id=proj.project_id).first()
    if not alloc:
        alloc = FundingAllocation(
            allocation_id=uid(),
            admin_id=admin_id,
            project_id=proj.project_id,
            total_amount=total,
            equipment_amount=equipment,
            materials_amount=materials,
            travel_amount=travel,
            other_amount=other,
            allocation_date=now_utc(),
            allocation_status=allocation_status.upper(),
        )
        db.session.add(alloc)
    else:
        alloc.allocation_status = allocation_status.upper()
        alloc.allocation_date = now_utc()
    db.session.commit()

    if allocation_status.upper() == "CONFIRMED":
        proposal.proposal_status = "FUNDED"
        db.session.commit()

    return proj, alloc

def add_progress_reports(project: Project, researcher_id: str, hod_id: str):
    # Two reports: one submitted, one pending HoD comment
    periods = [
        (date.today() - timedelta(days=60), date.today() - timedelta(days=30), "SUBMITTED", "Good progress; continue."),
        (date.today() - timedelta(days=30), date.today(), "UNDER REVIEW", ""),
    ]
    for ps, pe, st, hod_comment in periods:
        exists = ProgressReport.query.filter_by(project_id=project.project_id, period_start_date=ps, period_end_date=pe).first()
        if exists:
            continue
        db.session.add(ProgressReport(
            progress_id=uid(),
            project_id=project.project_id,
            researcher_id=researcher_id,
            hod_id=hod_id,
            period_start_date=ps,
            period_end_date=pe,
            summary="Implemented milestone features and validated expected outputs with pilot users.",
            milestones_achieved="User onboarding; proposal submission; reviewer assignment workflow tested.",
            challenges="Minor UI alignment issues; addressed with CSS fixes and form validation updates.",
            resource_usage="Budget tracking within approved limits; no additional equipment purchases required.",
            submission_date=now_utc() - timedelta(days=3),
            status=st,
            hod_comments=hod_comment or "Pending HoD review.",
        ))
    db.session.commit()

# -------------------------
# Main seeding routine
# -------------------------

def run():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # -------------------------
        # 1) Admin
        # -------------------------
        admin_user = get_or_create_user("admin@researchly.demo", "Admin Demo", "1234")
        upsert_profile(admin_user.id, "ADMIN", "ACTIVE", department_name=None)
        admin_row = ensure_role_row("ADMIN", admin_user.id)

        log_activity("Database reset and demo data seeding started.", action="SEED_START", actor_user_id=admin_user.id, created_at=dt_utc(minutes_ago=25))

        # -------------------------
        # 2) Departments + HOD
        # -------------------------
        hod_user = get_or_create_user("prof.hakim@researchly.demo", "Prof. Hakim Zulkifli", "demo123")
        upsert_profile(
            hod_user.id, "HOD", "ACTIVE",
            department_name="Computer Science",
            contact_number="012-3456789",
            address="Faculty of Computing & Informatics, MMU Cyberjaya, 63000 Cyberjaya, Selangor",
            emergency_name="Nur Aina",
            emergency_number="013-9988776",
        )
        hod_row = ensure_role_row("HOD", hod_user.id)

        departments = [
            ("Computer Science", "Research and innovation in software engineering, AI, and cybersecurity."),
            ("Engineering", "Applied engineering research across networks, systems, and hardware."),
            ("Business", "Business analytics, entrepreneurship, and digital transformation studies."),
            ("Multimedia", "Human-computer interaction, multimedia systems, and creative computing."),
        ]
        dept_rows: list[Department] = []
        for name, desc in departments:
            # Use same HoD for demo simplicity; easy to expand to multiple HoDs later.
            dept_rows.append(get_or_create_department(name, desc, hod_row.hod_id))

        log_activity("Departments and HoD profiles created.", action="SEED_DEPARTMENTS", actor_user_id=admin_user.id, created_at=dt_utc(minutes_ago=23))

        # -------------------------
        # 3) Reviewers
        # -------------------------
        reviewer_specs = [
            ("nur.farhana@researchly.demo", "Nur Farhana Ismail", "demo123", "Cybersecurity, Digital Forensics, Risk Assessment"),
            ("daniel.ong@researchly.demo", "Daniel Ong Wei Jian", "demo123", "AI, Data Science, Machine Learning"),
            ("meera.nair@researchly.demo", "Meera Nair", "demo123", "UI/UX, HCI, User Research"),
            ("amirul.hadi@researchly.demo", "Amirul Hadi", "demo123", "Networks, Cloud Systems, DevOps"),
        ]

        reviewer_rows: list[Reviewer] = []
        for email, name, pw, tags in reviewer_specs:
            ru = get_or_create_user(email, name, pw)
            upsert_profile(
                ru.id, "REVIEWER", "ACTIVE",
                department_name=RND.choice(["Computer Science", "Engineering", "Multimedia"]),
                expertise_tags=tags,
                contact_number=f"01{RND.randint(0,9)}-{RND.randint(1000000,9999999)}",
                address=RND.choice([
                    "Taman Putra Perdana, 47130 Puchong, Selangor",
                    "Setia Alam, 40170 Shah Alam, Selangor",
                    "Presint 9, 62250 Putrajaya",
                ])
            )
            reviewer_rows.append(ensure_role_row("REVIEWER", ru.id))

        log_activity("Reviewer accounts created.", action="SEED_REVIEWERS", actor_user_id=admin_user.id, created_at=dt_utc(minutes_ago=22))

        # -------------------------
        # 4) Researchers (+ bank accounts)
        # -------------------------
        researcher_specs = [
            ("aisyah.rahman@researchly.demo", "Aisyah Rahman", "demo123", "Computer Science", "Public Bank", "PB-338001234567"),
            ("liam.tan@researchly.demo", "Liam Tan", "demo123", "Engineering", "Maybank", "MB-118009876543"),
            ("syafiq.firdaus@researchly.demo", "Syafiq Firdaus", "demo123", "Business", "CIMB Bank", "CIMB-880012340001"),
            ("sarah.lim@researchly.demo", "Sarah Lim", "demo123", "Multimedia", "RHB Bank", "RHB-450098761122"),
        ]

        researcher_rows: list[Researcher] = []
        for email, name, pw, dept, bank_name, acc_no in researcher_specs:
            u = get_or_create_user(email, name, pw)
            upsert_profile(
                u.id, "RESEARCHER", "ACTIVE",
                department_name=dept,
                contact_number=f"01{RND.randint(0,9)}-{RND.randint(1000000,9999999)}",
                address=RND.choice([
                    "No. 25, Jalan Mutiara 2, 47100 Puchong, Selangor",
                    "Apartment C-8-3, Cyberia Smarthomes, 63000 Cyberjaya, Selangor",
                    "No. 18, Jalan PJU 10/7, Damansara Damai, 47830 Petaling Jaya, Selangor",
                ]),
                emergency_name=RND.choice(["Haziq Rahman", "Nur Izzati", "Tan Mei Ling", "Ahmad Syukri"]),
                emergency_number=f"01{RND.randint(0,9)}-{RND.randint(1000000,9999999)}",
            )
            r = ensure_role_row("RESEARCHER", u.id)

            bank = get_or_create_bank(acc_no, bank_name)
            r.bank_account_number = bank.bank_account_number
            db.session.commit()

            researcher_rows.append(r)

        # Pending + deactivated accounts to test admin user management tabs
        pending_u = get_or_create_user("pending.user@researchly.demo", "Pending User", "demo123")
        upsert_profile(pending_u.id, "UNASSIGNED", "PENDING", department_name=None)
        deact_u = get_or_create_user("deactivated.user@researchly.demo", "Deactivated User", "demo123")
        upsert_profile(deact_u.id, "RESEARCHER", "DEACTIVATED", department_name="Computer Science")

        log_activity("Researcher accounts created (plus pending/deactivated users).", action="SEED_USERS", actor_user_id=admin_user.id, created_at=dt_utc(minutes_ago=21))

        # -------------------------
        # 5) Grant Schemes
        # -------------------------
        schemes: dict[tuple[str, str], GrantScheme] = {}
        for dept in dept_rows:
            schemes[(dept.department_name, "OPEN")] = create_scheme(admin_row.admin_id, dept, status="OPEN")

        # extras for testing filters/status tabs
        schemes[(dept_rows[0].department_name, "CLOSED")] = create_scheme(admin_row.admin_id, dept_rows[0], status="CLOSED")
        schemes[(dept_rows[1].department_name, "DRAFT")] = create_scheme(admin_row.admin_id, dept_rows[1], status="DRAFT")

        log_activity("Grant schemes created (OPEN/CLOSED/DRAFT).", action="SEED_SCHEMES", actor_user_id=admin_user.id, created_at=dt_utc(minutes_ago=20))

        # -------------------------
        # 6) Proposals: admin workflow coverage
        #    We create a set per department with different workflow states so compute_proposal_display_status() returns:
        #    Pending Assignment / Pending Review / Pending Endorsement / Pending Approval / Pending Funding / Funded / Rejected
        # -------------------------
        workflow_cases = [
            ("Pending Assignment",      dict(assign=False, reviews=False, hod=False, final=None, funding=None)),
            ("Pending Review",          dict(assign=True,  reviews=False, hod=False, final=None, funding=None)),
            ("Pending Endorsement",     dict(assign=True,  reviews=True,  hod=False, final=None, funding=None)),
            ("Pending Approval",        dict(assign=True,  reviews=True,  hod=True,  final=None, funding=None)),
            ("Pending Funding (none)",  dict(assign=True,  reviews=True,  hod=True,  final="APPROVED", funding=None)),
            ("Pending Funding (draft)", dict(assign=True,  reviews=True,  hod=True,  final="APPROVED", funding="DRAFT")),
            ("Funded",                  dict(assign=True,  reviews=True,  hod=True,  final="APPROVED", funding="CONFIRMED")),
            ("Rejected",                dict(assign=True,  reviews=True,  hod=True,  final="REJECTED", funding=None)),
        ]

        minute_cursor = 180  # stagger submissions for nicer ordering
        for dept in dept_rows:
            scheme = schemes[(dept.department_name, "OPEN")]
            for idx, (label, flags) in enumerate(workflow_cases, start=1):
                # round-robin researchers
                researcher = researcher_rows[(idx - 1) % len(researcher_rows)]
                title = f"{dept.department_name}: {label} — Smart Workflow Validation #{idx}"
                budget = RND.choice([12000, 18000, 25000, 32000, 45000, 60000])

                p = create_proposal(
                    scheme.scheme_id,
                    researcher.researcher_id,
                    title,
                    status="Pending Review",  # base; admin display status is derived from workflow tables
                    submitted_at=dt_utc(minutes_ago=minute_cursor),
                    requested_budget=budget,
                )
                minute_cursor -= 7

                clear_workflow(p.proposal_id)

                # Attachments (so researcher/proposal pages have files to list)
                add_attachment(p.proposal_id, "Research_Proposal.txt", "proposal")
                add_attachment(p.proposal_id, "Budget_Breakdown.txt", "budget")

                # Build workflow state
                if flags["assign"]:
                    assign_reviewers(p.proposal_id, reviewer_rows, count=2)
                if flags["reviews"]:
                    add_reviews(p.proposal_id, reviewer_rows, count=2, approve_ratio=1.0)
                if flags["hod"]:
                    add_hod_endorsement(
                        p.proposal_id, hod_row.hod_id, "ENDORSE",
                        "Endorsed with minor revisions to milestones and risk section."
                    )
                if flags["final"]:
                    set_final_decision(p.proposal_id, admin_row.admin_id, flags["final"])
                if flags["funding"]:
                    create_project_and_funding(p, admin_row.admin_id, allocation_status=flags["funding"])

                # Activity logs (admin dashboard recent activity)
                log_activity(
                    f"Seeded proposal '{p.project_title}' for {dept.department_name}.",
                    action="SEED_PROPOSAL",
                    proposal_id=p.proposal_id,
                    actor_user_id=admin_user.id,
                    created_at=dt_utc(minutes_ago=minute_cursor),
                )

        # -------------------------
        # 7) Researcher-side statuses (Draft / Under Review / Revision Required)
        #    These are used by researcher dashboard counts/labels.
        # -------------------------
        r0_user = User.query.filter_by(email="aisyah.rahman@researchly.demo").first()
        r0 = Researcher.query.filter_by(user_id=r0_user.id).first()
        cs_open_scheme = schemes[("Computer Science", "OPEN")]

        researcher_status_set = [
            ("Draft", "Draft — Privacy-Preserving Audit Logs", 8000),
            ("Under Review", "Under Review — Secure Grant Workflow Model", 22000),
            ("Revision Required", "Revision Required — UI Consistency & Accessibility", 15000),
            ("Rejected", "Rejected — Overbudgeted Prototype Plan", 90000),
            ("FUNDED", "Funded — Lightweight Reporting Automation", 30000),
        ]

        for i, (st, title, budget) in enumerate(researcher_status_set, start=1):
            p = create_proposal(
                cs_open_scheme.scheme_id,
                r0.researcher_id,
                f"Aisyah: {title}",
                status=st,
                submitted_at=dt_utc(days_ago=RND.randint(1, 14), minutes_ago=RND.randint(0, 500)),
                requested_budget=budget,
            )
            add_attachment(p.proposal_id, "Supporting_Letter.txt", "support")

            # If FUNDED, create project+confirmed allocation so display is consistent
            if st.upper() == "FUNDED":
                clear_workflow(p.proposal_id)
                set_final_decision(p.proposal_id, admin_row.admin_id, "APPROVED")
                create_project_and_funding(p, admin_row.admin_id, allocation_status="CONFIRMED")

        log_activity("Researcher status variety seeded (Draft/Under Review/Revision/Funded).", action="SEED_RESEARCHER_STATUSES", actor_user_id=admin_user.id, created_at=dt_utc(minutes_ago=12))

        # -------------------------
        # 8) Progress reports (for an ongoing funded project)
        # -------------------------
        funded_prop = Proposal.query.filter(Proposal.proposal_status.ilike("funded")).order_by(Proposal.submission_date.desc()).first()
        if funded_prop:
            proj = Project.query.filter_by(proposal_id=funded_prop.proposal_id).first()
            if proj:
                add_progress_reports(proj, funded_prop.researcher_id, hod_row.hod_id)
                log_activity(f"Progress reports seeded for funded project linked to '{funded_prop.project_title}'.", action="SEED_PROGRESS", proposal_id=funded_prop.proposal_id, actor_user_id=admin_user.id, created_at=dt_utc(minutes_ago=10))

        # -------------------------
        # 9) Notifications (unread + read mix)
        # -------------------------
        create_notif(admin_user.id, "3 new user registrations are pending approval.", "ADMIN", is_read=False, created_at=dt_utc(minutes_ago=6))
        create_notif(admin_user.id, "A grant scheme was auto-closed after its deadline.", "SYSTEM", is_read=True, created_at=dt_utc(days_ago=2))
        create_notif(r0_user.id, "Your proposal 'Aisyah: Under Review — Secure Grant Workflow Model' is under review.", "PROPOSAL", is_read=False, created_at=dt_utc(minutes_ago=8))
        create_notif(r0_user.id, "Revision requested: please update methodology and timeline section.", "PROPOSAL", is_read=False, created_at=dt_utc(days_ago=3))
        create_notif(hod_user.id, "A proposal is awaiting your endorsement decision.", "HOD", is_read=False, created_at=dt_utc(minutes_ago=9))

        log_activity("Notifications created for multiple roles.", action="SEED_NOTIFICATIONS", actor_user_id=admin_user.id, created_at=dt_utc(minutes_ago=8))

        db.session.commit()

        # -------------------------
        # Print credentials
        # -------------------------
        print("✅ Demo data seeded successfully!")
        print("Login credentials:")
        print("  Admin:      admin@researchly.demo / 1234")
        print("  Researcher: aisyah.rahman@researchly.demo / demo123")
        print("  Reviewer:   nur.farhana@researchly.demo / demo123")
        print("  HOD:        prof.hakim@researchly.demo / demo123")


if __name__ == "__main__":
    run()
