# seed_demo_data.py
from datetime import datetime, timezone, date, timedelta
import uuid

from main import (
    app, db, bcrypt,
    User, UserProfile,
    Admin, HOD, Reviewer, Researcher,
    Department, GrantScheme, Proposal,
    ReviewersAssignment, Review, HODEndorsement, FinalDecision,
    Project, FundingAllocation
)

# -------------------------
# Helpers
# -------------------------
def uid():
    return str(uuid.uuid4())

def hash_pw(pw: str) -> str:
    return bcrypt.generate_password_hash(pw).decode("utf-8")

def get_or_create_user(email, full_name, password_plain="demo"):
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(id=uid(), full_name=full_name, email=email, password=hash_pw(password_plain))
        db.session.add(u)
        db.session.commit()
    return u

def upsert_profile(user_id, role, account_status):
    prof = UserProfile.query.filter_by(user_id=user_id).first()
    if not prof:
        db.session.add(UserProfile(user_id=user_id, role=role, account_status=account_status))
    else:
        prof.role = role
        prof.account_status = account_status
    db.session.commit()

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
    desc = f"Demo Grant Scheme ({dept.department_name}) - {status}"
    scheme = GrantScheme.query.filter_by(description=desc).first()
    if scheme:
        return scheme

    scheme = GrantScheme(
        scheme_id=uid(),
        admin_id=admin_id,
        department_id=dept.department_id,
        description=desc,
        eligibiliity="MMU Staff / Researchers",
        open_date=date.today() - timedelta(days=14),
        close_date=date.today() + timedelta(days=30) if status == "OPEN" else date.today() - timedelta(days=1),
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
        abstract="Demo abstract for testing.",
        methodology="Demo methodology section for testing.",
        requested_budget=budget,
        submission_date=datetime.now(timezone.utc),
        proposal_status="SUBMITTED"
    )
    db.session.add(proposal)
    db.session.commit()
    return proposal

def clear_workflow(proposal_id: str):
    # Remove everything so it becomes "Pending Assignment"
    Review.query.filter_by(proposal_id=proposal_id).delete()
    ReviewersAssignment.query.filter_by(proposal_id=proposal_id).delete()
    HODEndorsement.query.filter_by(proposal_id=proposal_id).delete()
    FinalDecision.query.filter_by(proposal_id=proposal_id).delete()

    # Also remove funding/project if any
    proj = Project.query.filter_by(proposal_id=proposal_id).first()
    if proj:
        FundingAllocation.query.filter_by(project_id=proj.project_id).delete()
        db.session.delete(proj)

    db.session.commit()

def add_assignments_only(proposal_id: str, reviewers, count=2):
    # Pending Review (assigned but no reviews)
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
    # Ensure assignments exist
    add_assignments_only(proposal_id, reviewers, count=count)

    # Add reviews => now can become "Pending Endorsement" (if no HOD endorsement)
    for rv in reviewers[:count]:
        if not Review.query.filter_by(proposal_id=proposal_id, reviewer_id=rv.reviewer_id).first():
            db.session.add(Review(
                review_id=uid(),
                proposal_id=proposal_id,
                reviewer_id=rv.reviewer_id,
                review_date=datetime.now(timezone.utc),
                recommendation="APPROVE",
                feedback="Demo feedback."
            ))
    db.session.commit()

def add_hod_endorsement(proposal_id: str, hod_id: str, decision="ENDORSE"):
    # Pending Approval (endorsed but no FinalDecision)
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
    # Approved / Rejected (FinalDecision exists)
    fd = FinalDecision.query.filter_by(proposal_id=proposal_id).first()
    if not fd:
        db.session.add(FinalDecision(
            final_decision_id=uid(),
            proposal_id=proposal_id,
            admin_id=admin_id,
            decision=decision
        ))
    else:
        fd.decision = decision
    db.session.commit()

def create_funding(proposal: Proposal, admin_id: str, status: str):
    """
    status: "DRAFT" or "CONFIRMED"
    For CONFIRMED, we also set proposal.proposal_status="FUNDED" (matches your app logic).
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
            project_status="ONGOING"  
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
            allocation_status=status
        )
        db.session.add(alloc)
    else:
        alloc.allocation_status = status

    if status.upper() == "CONFIRMED":
        proposal.proposal_status = "FUNDED"

    db.session.commit()


# -------------------------
# Seeder
# -------------------------
def run():
    with app.app_context():
        # FULL RESET so all pages are consistent for testing
        db.drop_all()
        db.create_all()

        # ----------------------------
        # Admin account
        # ----------------------------
        admin_user = get_or_create_user("admin_demo@gmail.com", "Admin Demo", "1234")
        upsert_profile(admin_user.id, "ADMIN", "ACTIVE")
        admin = ensure_role_row("ADMIN", admin_user.id)

        # ----------------------------
        # Create some pending users (User Management testing)
        # ----------------------------
        for i in range(3):
            u = get_or_create_user(f"pending_user{i+1}@gmail.com", f"Pending User {i+1}", "demo")
            upsert_profile(u.id, "RESEARCHER", "PENDING")

        # ----------------------------
        # Departments + HODs
        # ----------------------------
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

        # ----------------------------
        # Reviewers (pool)
        # ----------------------------
        reviewers = []
        for i in range(4):
            ru = get_or_create_user(f"reviewer{i+1}@gmail.com", f"Reviewer {i+1}", "demo")
            upsert_profile(ru.id, "REVIEWER", "ACTIVE")
            reviewers.append(ensure_role_row("REVIEWER", ru.id))

        # ----------------------------
        # Schemes (one OPEN + one CLOSED for 2 depts to test scheme page)
        # ----------------------------
        schemes = {}
        for dept, hod in departments:
            schemes[(dept.department_name, "OPEN")] = create_scheme(admin.admin_id, dept, status="OPEN")
        # extra closed schemes
        for dept, hod in departments[:2]:
            schemes[(dept.department_name, "CLOSED")] = create_scheme(admin.admin_id, dept, status="CLOSED")

        # ----------------------------
        # Create proposals in ALL workflow states per some departments
        # ----------------------------
        # status -> what to create:
        # Pending Assignment: nothing extra
        # Pending Review: assignments only
        # Pending Endorsement: assignments + reviews (no HOD endorsement)
        # Pending Approval: endorsement exists (no FinalDecision)
        # Approved: final decision approved (no funding)
        # Funded Draft: approved + funding DRAFT
        # Funded Confirmed: approved + funding CONFIRMED
        # Rejected: final decision rejected

        demo_cases = [
            ("Pending Assignment", 12000),
            ("Pending Review", 14000),
            ("Pending Endorsement", 15000),
            ("Pending Approval", 16000),
            ("Approved", 17000),
            ("Funded Draft", 18000),
            ("Funded Confirmed", 19000),
            ("Rejected", 20000),
        ]

        researcher_counter = 1

        for dept, hod in departments:
            scheme = schemes[(dept.department_name, "OPEN")]

            for case_name, budget in demo_cases:
                # Create a researcher for each proposal (simple, consistent)
                r_user = get_or_create_user(
                    f"researcher{researcher_counter}@gmail.com",
                    f"Researcher {researcher_counter}",
                    "demo"
                )
                upsert_profile(r_user.id, "RESEARCHER", "ACTIVE")
                researcher = ensure_role_row("RESEARCHER", r_user.id)
                researcher_counter += 1

                title = f"[{case_name}] Demo Proposal ({dept.department_name})"

                proposal = create_proposal(
                    scheme_id=scheme.scheme_id,
                    researcher_id=researcher.researcher_id,
                    title=title,
                    budget=budget
                )

                # Clear any workflow records (idempotent)
                clear_workflow(proposal.proposal_id)

                # Build workflow state
                if case_name == "Pending Assignment":
                    pass

                elif case_name == "Pending Review":
                    add_assignments_only(proposal.proposal_id, reviewers, count=2)

                elif case_name == "Pending Endorsement":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    # no HOD endorsement

                elif case_name == "Pending Approval":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    add_hod_endorsement(proposal.proposal_id, hod.hod_id, decision="ENDORSE")
                    # no FinalDecision

                elif case_name == "Approved":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    add_hod_endorsement(proposal.proposal_id, hod.hod_id, decision="ENDORSE")
                    set_final_decision(proposal.proposal_id, admin.admin_id, "APPROVED")
                    # no funding

                elif case_name == "Funded Draft":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    add_hod_endorsement(proposal.proposal_id, hod.hod_id, decision="ENDORSE")
                    set_final_decision(proposal.proposal_id, admin.admin_id, "APPROVED")
                    create_funding(proposal, admin.admin_id, status="DRAFT")

                elif case_name == "Funded Confirmed":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    add_hod_endorsement(proposal.proposal_id, hod.hod_id, decision="ENDORSE")
                    set_final_decision(proposal.proposal_id, admin.admin_id, "APPROVED")
                    create_funding(proposal, admin.admin_id, status="CONFIRMED")

                elif case_name == "Rejected":
                    add_reviews_for_assignments(proposal.proposal_id, reviewers, count=2)
                    add_hod_endorsement(proposal.proposal_id, hod.hod_id, decision="ENDORSE")
                    set_final_decision(proposal.proposal_id, admin.admin_id, "REJECTED")

        print("✅ Demo data seeded successfully!")
        print("✅ Admin login: admin_demo@gmail.com / 1234")
        print("✅ Created workflow states for Proposal List + Assign Reviewers + Final Approval + Funding Allocation.")
        print("✅ Created PENDING users for User Management testing.")

if __name__ == "__main__":
    run()
