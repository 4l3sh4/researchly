from datetime import datetime, timezone, date, timedelta
import uuid

from main import (
    app, db, bcrypt,
    User, UserProfile,
    Admin, HOD, Reviewer, Researcher,
    Department, GrantScheme, Proposal,
    ReviewersAssignment, Review, HODEndorsement, FinalDecision,
    Project, FundingAllocation,
    ActivityLog,  # ✅ Option A dashboard uses ActivityLog
)

# =========================================================
# Demo Seeder for "Researchly" Admin routes
# - Resets DB (drop_all/create_all)
# - Creates users in PENDING/ACTIVE/DEACTIVATED for user management
# - Creates departments + HOD
# - Creates reviewers with expertise_tags for filtering
# - Creates grant schemes (OPEN / CLOSED / DRAFT)
# - Creates proposals across workflow states that match compute_proposal_display_status()
# - Creates ActivityLog entries so Admin Dashboard "Recent Activity" updates
# =========================================================

def uid() -> str:
    return str(uuid.uuid4())

def hash_pw(pw: str) -> str:
    return bcrypt.generate_password_hash(pw).decode("utf-8")

def log(msg: str, action="SEED", proposal_id=None, actor_user_id=None, created_at=None):
    row = ActivityLog(
        activity_id=uid(),
        created_at=created_at or datetime.now(timezone.utc),
        actor_user_id=actor_user_id,
        proposal_id=proposal_id,
        action=action,
        message=msg,
    )
    db.session.add(row)

def get_or_create_user(email: str, full_name: str, password_plain="demo"):
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(id=uid(), full_name=full_name, email=email, password=hash_pw(password_plain))
        db.session.add(u)
        db.session.commit()
    return u

def upsert_profile(user_id: str, role: str, account_status: str, expertise_tags: str | None = None):
    prof = UserProfile.query.filter_by(user_id=user_id).first()
    if not prof:
        prof = UserProfile(user_id=user_id, role=role, account_status=account_status)
        db.session.add(prof)
    else:
        prof.role = role
        prof.account_status = account_status

    # Optional for reviewer filter UI
    if expertise_tags is not None:
        prof.expertise_tags = expertise_tags

    db.session.commit()
    return prof

def ensure_role_row(role: str, user_id: str):
    role = role.upper()

    if role == "ADMIN":
        row = Admin.query.filter_by(user_id=user_id).first()
        if not row:
            row = Admin(user_id=user_id)
            db.session.add(row)
            db.session.commit()
        return row

    if role == "HOD":
        row = HOD.query.filter_by(user_id=user_id).first()
        if not row:
            row = HOD(user_id=user_id)
            db.session.add(row)
            db.session.commit()
        return row

    if role == "REVIEWER":
        row = Reviewer.query.filter_by(user_id=user_id).first()
        if not row:
            row = Reviewer(user_id=user_id)
            db.session.add(row)
            db.session.commit()
        return row

    if role == "RESEARCHER":
        row = Researcher.query.filter_by(user_id=user_id).first()
        if not row:
            row = Researcher(user_id=user_id)
            db.session.add(row)
            db.session.commit()
        return row

    raise ValueError(f"Unknown role: {role}")

def get_or_create_department(dept_name: str, dept_desc: str, hod_id: str):
    dept = Department.query.filter_by(department_name=dept_name).first()
    if dept:
        dept.hod_id = hod_id
        db.session.commit()
        return dept

    dept = Department(
        department_id=uid(),
        hod_id=hod_id,
        department_name=dept_name,
        department_description=dept_desc
    )
    db.session.add(dept)
    db.session.commit()
    return dept

def create_scheme(admin_id: str, dept: Department, status="OPEN"):
    """
    status: OPEN / CLOSED / DRAFT
    """
    desc = f"Demo Grant Scheme ({dept.department_name}) - {status}"
    scheme = GrantScheme.query.filter_by(description=desc).first()
    if scheme:
        scheme.scheme_status = status
        db.session.commit()
        return scheme

    open_date = date.today() - timedelta(days=14)
    close_date = date.today() + timedelta(days=30)
    if status == "CLOSED":
        close_date = date.today() - timedelta(days=1)

    scheme = GrantScheme(
        scheme_id=uid(),
        admin_id=admin_id,
        department_id=dept.department_id,
        description=desc,
        eligibiliity="MMU Staff / Researchers",
        open_date=open_date,
        close_date=close_date,
        max_budget=50000,
        project_duration_limit=12,
        required_documents="Proposal, CV, Budget",
        reporting_requirements="Monthly report, Final report",
        scheme_status=status,
    )
    db.session.add(scheme)
    db.session.commit()
    return scheme

def create_proposal(scheme_id: str, researcher_id: str, title: str, budget: int):
    proposal = Proposal.query.filter_by(project_title=title).first()
    if proposal:
        return proposal

    proposal = Proposal(
        proposal_id=uid(),
        scheme_id=scheme_id,
        researcher_id=researcher_id,
        project_title=title,
        abstract="Demo abstract for testing admin routes.",
        methodology="Demo methodology section for testing admin routes.",
        requested_budget=budget,
        submission_date=datetime.now(timezone.utc),
        proposal_status="SUBMITTED"
    )
    db.session.add(proposal)
    db.session.commit()
    return proposal

def clear_workflow(proposal_id: str):
    Review.query.filter_by(proposal_id=proposal_id).delete()
    ReviewersAssignment.query.filter_by(proposal_id=proposal_id).delete()
    HODEndorsement.query.filter_by(proposal_id=proposal_id).delete()
    FinalDecision.query.filter_by(proposal_id=proposal_id).delete()

    proj = Project.query.filter_by(proposal_id=proposal_id).first()
    if proj:
        FundingAllocation.query.filter_by(project_id=proj.project_id).delete()
        db.session.delete(proj)

    p = db.session.get(Proposal, proposal_id)
    if p:
        p.proposal_status = "SUBMITTED"

    db.session.commit()

def add_assignments_only(proposal_id: str, reviewers, count=2):
    for rv in reviewers[:count]:
        if not ReviewersAssignment.query.filter_by(proposal_id=proposal_id, reviewer_id=rv.reviewer_id).first():
            db.session.add(ReviewersAssignment(
                assignment_id=uid(),
                proposal_id=proposal_id,
                reviewer_id=rv.reviewer_id,
                assignment_status="ASSIGNED"
            ))
    db.session.commit()

def add_reviews_for_assignments(proposal_id: str, reviewers, count=2):
    add_assignments_only(proposal_id, reviewers, count=count)

    for rv in reviewers[:count]:
        if not Review.query.filter_by(proposal_id=proposal_id, reviewer_id=rv.reviewer_id).first():
            db.session.add(Review(
                review_id=uid(),
                proposal_id=proposal_id,
                reviewer_id=rv.reviewer_id,
                review_date=datetime.now(timezone.utc),
                recommendation="APPROVE",
                feedback="Demo review feedback."
            ))
    db.session.commit()

def add_hod_endorsement(proposal_id: str, hod_id: str, decision="ENDORSE"):
    if not HODEndorsement.query.filter_by(proposal_id=proposal_id).first():
        db.session.add(HODEndorsement(
            hod_endorsement_id=uid(),
            hod_id=hod_id,
            proposal_id=proposal_id,
            decision=decision,
            remarks="Demo HoD remarks."
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
            decision_date=datetime.now(timezone.utc),
        ))
    else:
        fd.decision = decision
        fd.decision_date = datetime.now(timezone.utc)

    p = db.session.get(Proposal, proposal_id)
    if p and decision.upper() == "REJECTED":
        p.proposal_status = "REJECTED"

    db.session.commit()

def create_funding(proposal: Proposal, admin_id: str, status: str):
    """
    status: DRAFT or CONFIRMED
    - DRAFT -> display stays Pending Funding
    - CONFIRMED -> proposal.proposal_status becomes FUNDED (display Funded)
    """
    proj = Project.query.filter_by(proposal_id=proposal.proposal_id).first()
    if not proj:
        proj = Project(
            project_id=uid(),
            proposal_id=proposal.proposal_id,
            researcher_id=proposal.researcher_id,
            scheme_id=proposal.scheme_id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=180),
            project_status="DRAFT" if status.upper() == "DRAFT" else "ONGOING"
        )
        db.session.add(proj)
        db.session.commit()

    alloc = FundingAllocation.query.filter_by(project_id=proj.project_id).first()
    if not alloc:
        alloc = FundingAllocation(
            allocation_id=uid(),
            admin_id=admin_id,
            project_id=proj.project_id,
            total_amount=proposal.requested_budget,
            equipment_amount=int(proposal.requested_budget * 0.3),
            materials_amount=int(proposal.requested_budget * 0.3),
            travel_amount=int(proposal.requested_budget * 0.2),
            other_amount=int(proposal.requested_budget * 0.2),
            allocation_date=datetime.now(timezone.utc),
            allocation_status=status.upper(),
        )
        db.session.add(alloc)
    else:
        alloc.allocation_status = status.upper()
        alloc.allocation_date = datetime.now(timezone.utc)

    if status.upper() == "CONFIRMED":
        proposal.proposal_status = "FUNDED"

    db.session.commit()


def run():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Admin login
        admin_user = get_or_create_user("admin_demo@gmail.com", "Admin Demo", "1234")
        upsert_profile(admin_user.id, "ADMIN", "ACTIVE")
        admin = ensure_role_row("ADMIN", admin_user.id)

        # User management states
        for i in range(3):
            u = get_or_create_user(f"pending_user{i+1}@gmail.com", f"Pending User {i+1}", "demo")
            upsert_profile(u.id, "RESEARCHER", "PENDING")

        for i in range(2):
            u = get_or_create_user(f"active_user{i+1}@gmail.com", f"Active User {i+1}", "demo")
            upsert_profile(u.id, "RESEARCHER", "ACTIVE")

        for i in range(2):
            u = get_or_create_user(f"deact_user{i+1}@gmail.com", f"Deactivated User {i+1}", "demo")
            upsert_profile(u.id, "RESEARCHER", "DEACTIVATED")

        # Departments + HOD
        dept_specs = [
            ("Computer Science", "Demo CS Dept"),
            ("Engineering", "Demo Engineering Dept"),
            ("Business", "Demo Business Dept"),
            ("Management", "Demo Management Dept"),
            ("Multimedia", "Demo Multimedia Dept"),
        ]

        departments = []
        for dept_name, dept_desc in dept_specs:
            hod_user = get_or_create_user(
                f"hod_{dept_name.lower().replace(' ', '_')}@gmail.com",
                f"HOD {dept_name}",
                "demo"
            )
            upsert_profile(hod_user.id, "HOD", "ACTIVE")
            hod = ensure_role_row("HOD", hod_user.id)

            dept = get_or_create_department(dept_name, dept_desc, hod.hod_id)
            departments.append((dept, hod))

        # Reviewers + expertise tags
        reviewer_specs = [
            ("reviewer1@gmail.com", "Reviewer 1", "AI, Data Science"),
            ("reviewer2@gmail.com", "Reviewer 2", "Cybersecurity, AI"),
            ("reviewer3@gmail.com", "Reviewer 3", "Finance, Analytics"),
            ("reviewer4@gmail.com", "Reviewer 4", "UI/UX, Game Design"),
        ]
        reviewers = []
        for email, name, tags in reviewer_specs:
            ru = get_or_create_user(email, name, "demo")
            upsert_profile(ru.id, "REVIEWER", "ACTIVE", expertise_tags=tags)
            reviewers.append(ensure_role_row("REVIEWER", ru.id))

        # Grant schemes (OPEN everywhere) + extras CLOSED/DRAFT
        schemes = {}
        for dept, _hod in departments:
            schemes[(dept.department_name, "OPEN")] = create_scheme(admin.admin_id, dept, status="OPEN")

        for dept, _hod in departments[:2]:
            schemes[(dept.department_name, "CLOSED")] = create_scheme(admin.admin_id, dept, status="CLOSED")
        for dept, _hod in departments[2:4]:
            schemes[(dept.department_name, "DRAFT")] = create_scheme(admin.admin_id, dept, status="DRAFT")

        # Proposal states for admin routes
        demo_cases = [
            ("Pending Assignment", 12000),
            ("Pending Review", 14000),
            ("Pending Endorsement", 15000),
            ("Pending Approval", 16000),
            ("Pending Funding (No Allocation)", 17000),
            ("Pending Funding (Draft Allocation)", 18000),
            ("Funded (Confirmed)", 19000),
            ("Rejected", 20000),
        ]

        researcher_counter = 1
        now = datetime.now(timezone.utc)

        for dept, hod in departments:
            scheme = schemes[(dept.department_name, "OPEN")]

            for case_name, budget in demo_cases:
                r_user = get_or_create_user(
                    f"researcher{researcher_counter}@gmail.com",
                    f"Researcher {researcher_counter}",
                    "demo"
                )
                upsert_profile(r_user.id, "RESEARCHER", "ACTIVE")
                researcher = ensure_role_row("RESEARCHER", r_user.id)
                researcher_counter += 1

                title = f"[{case_name}] Demo Proposal ({dept.department_name})"
                proposal = create_proposal(scheme.scheme_id, researcher.researcher_id, title, budget)

                clear_workflow(proposal.proposal_id)

                if case_name == "Pending Assignment":
                    pass

                elif case_name == "Pending Review":
                    add_assignments_only(proposal.proposal_id, reviewers, count=2)

                elif case_name == "Pending Endorsement":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)

                elif case_name == "Pending Approval":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    add_hod_endorsement(proposal.proposal_id, hod.hod_id, decision="ENDORSE")

                elif case_name == "Pending Funding (No Allocation)":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    add_hod_endorsement(proposal.proposal_id, hod.hod_id, decision="ENDORSE")
                    set_final_decision(proposal.proposal_id, admin.admin_id, "APPROVED")

                elif case_name == "Pending Funding (Draft Allocation)":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    add_hod_endorsement(proposal.proposal_id, hod.hod_id, decision="ENDORSE")
                    set_final_decision(proposal.proposal_id, admin.admin_id, "APPROVED")
                    create_funding(proposal, admin.admin_id, status="DRAFT")

                elif case_name == "Funded (Confirmed)":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    add_hod_endorsement(proposal.proposal_id, hod.hod_id, decision="ENDORSE")
                    set_final_decision(proposal.proposal_id, admin.admin_id, "APPROVED")
                    create_funding(proposal, admin.admin_id, status="CONFIRMED")

                elif case_name == "Rejected":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    add_hod_endorsement(proposal.proposal_id, hod.hod_id, decision="ENDORSE")
                    set_final_decision(proposal.proposal_id, admin.admin_id, "REJECTED")

                # Seed log per proposal (stagger timestamps)
                base_time = now - timedelta(minutes=(researcher_counter * 2))
                log(f"Seeded proposal: {proposal.project_title}", action="SEED_PROPOSAL", proposal_id=proposal.proposal_id, actor_user_id=admin_user.id, created_at=base_time)

        # Extra logs (recent activity list)
        sample_prop = Proposal.query.order_by(Proposal.submission_date.desc()).first()
        if sample_prop:
            log(f"Proposal '{sample_prop.project_title}' assigned to Reviewer 1", action="ASSIGN_REVIEWER", proposal_id=sample_prop.proposal_id, actor_user_id=admin_user.id, created_at=now - timedelta(minutes=3))
            log(f"Final decision Approved for '{sample_prop.project_title}'", action="FINAL_DECISION", proposal_id=sample_prop.proposal_id, actor_user_id=admin_user.id, created_at=now - timedelta(minutes=2))
            log(f"Funding confirmed for '{sample_prop.project_title}' (Total: {sample_prop.requested_budget})", action="CONFIRM_FUNDING", proposal_id=sample_prop.proposal_id, actor_user_id=admin_user.id, created_at=now - timedelta(minutes=1))

        pending_any = UserProfile.query.filter_by(account_status="PENDING").first()
        if pending_any:
            u = db.session.get(User, pending_any.user_id)
            if u:
                log(f"User '{u.full_name}' approved and role set to RESEARCHER", action="APPROVE_USER", actor_user_id=admin_user.id, created_at=now - timedelta(minutes=4))

        db.session.commit()

        print("✅ Demo data seeded successfully!")
        print("✅ Admin login: admin_demo@gmail.com / 1234")

if __name__ == "__main__":
    run()
