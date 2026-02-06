# seed_demo_data.py
from datetime import datetime, timezone, date, timedelta
import uuid

from main import (
    app, db, bcrypt,
    User, UserProfile,
    Admin, HOD, Reviewer, Researcher,
    Department, GrantScheme, Proposal,
    ReviewersAssignment, Review, HODEndorsement, FinalDecision
)

# -------------------------
# Helpers
# -------------------------
def uid():
    return str(uuid.uuid4())

def hash_pw(pw: str) -> str:
    return bcrypt.generate_password_hash(pw).decode("utf-8")

def get_or_create_user_id(email, full_name, role, password_plain="demo", account_status="ACTIVE"):
    """
    Returns user_id only (avoids expired object issues).
    Ensures UserProfile exists & matches role/status.
    """
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(id=uid(), full_name=full_name, email=email, password=hash_pw(password_plain))
        db.session.add(u)
        db.session.add(UserProfile(user_id=u.id, role=role, account_status=account_status))
        db.session.commit()
        return u.id

    prof = UserProfile.query.filter_by(user_id=u.id).first()
    if not prof:
        db.session.add(UserProfile(user_id=u.id, role=role, account_status=account_status))
        db.session.commit()
    else:
        changed = False
        if prof.role != role:
            prof.role = role
            changed = True
        if prof.account_status != account_status:
            prof.account_status = account_status
            changed = True
        if changed:
            db.session.commit()

    return u.id

def ensure_role_row(role: str, user_id: str):
    """
    Ensure role table row exists (Admin/HOD/Reviewer/Researcher) and return it.
    """
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

def get_or_create_scheme_for_department(admin_id: str, dept_id: str, dept_name: str):
    desc = f"Demo Grant Scheme ({dept_name})"
    scheme = GrantScheme.query.filter_by(description=desc).first()
    if scheme:
        return scheme

    scheme = GrantScheme(
        scheme_id=uid(),
        admin_id=admin_id,
        department_id=dept_id,
        description=desc,
        eligibiliity="MMU Staff / Researchers",
        open_date=date.today() - timedelta(days=7),
        close_date=date.today() + timedelta(days=30),
        max_budget=50000,
        project_duration_limit=12,
        required_documents="Proposal, CV, Budget",
        reporting_requirements="Monthly report, Final report",
        scheme_status="OPEN",
    )
    db.session.add(scheme)
    db.session.commit()
    return scheme

def ensure_review_pipeline(proposal: Proposal, reviewers, budget: int, hod_id: str):
    """Ensure: assignments + reviews + HOD endorsement exist."""
    # 2 reviewers
    for rv in reviewers[:2]:
        if not ReviewersAssignment.query.filter_by(proposal_id=proposal.proposal_id, reviewer_id=rv.reviewer_id).first():
            db.session.add(ReviewersAssignment(
                assignment_id=uid(),
                proposal_id=proposal.proposal_id,
                reviewer_id=rv.reviewer_id,
                assignment_status="ASSIGNED"
            ))

        if not Review.query.filter_by(proposal_id=proposal.proposal_id, reviewer_id=rv.reviewer_id).first():
            db.session.add(Review(
                review_id=uid(),
                proposal_id=proposal.proposal_id,
                reviewer_id=rv.reviewer_id,
                review_date=datetime.now(timezone.utc),
                recommendation="APPROVE" if budget <= 15000 else "REVISE",
                feedback="Demo feedback for final approval testing."
            ))

    if not HODEndorsement.query.filter_by(proposal_id=proposal.proposal_id).first():
        db.session.add(HODEndorsement(
            hod_endorsement_id=uid(),
            hod_id=hod_id,
            proposal_id=proposal.proposal_id,
            decision="ENDORSE",
            remarks="Endorsed for demo final approval testing."
        ))

    db.session.commit()

def set_final_decision(proposal_id: str, admin_id: str, decision: str | None):
    """
    decision:
      - None => make it PENDING (delete FinalDecision if exists)
      - "APPROVED"/"REJECTED" => ensure record exists
    """
    existing = FinalDecision.query.filter_by(proposal_id=proposal_id).first()

    if decision is None:
        # Pending -> remove decision if exists
        if existing:
            db.session.delete(existing)
            db.session.commit()
        return

    # decided
    if not existing:
        db.session.add(FinalDecision(
            final_decision_id=uid(),
            proposal_id=proposal_id,
            admin_id=admin_id,
            decision=decision
        ))
    else:
        existing.decision = decision

    db.session.commit()

# -------------------------
# Seeder
# -------------------------
def run():
    with app.app_context():
        db.create_all()

        # ----------------------------
        # 1) Admin (login account)
        # ----------------------------
        admin_user_id = get_or_create_user_id(
            email="admin_demo@gmail.com",
            full_name="Admin Demo",
            role="ADMIN",
            password_plain="1234",
            account_status="ACTIVE"
        )
        admin = ensure_role_row("ADMIN", admin_user_id)

        # ----------------------------
        # 2) Departments + HODs
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
            hod_user_id = get_or_create_user_id(
                email=f"hod_{dept_name.lower().replace(' ', '_')}@gmail.com",
                full_name=f"HOD {dept_name}",
                role="HOD",
                password_plain="demo",
                account_status="ACTIVE"
            )
            hod = ensure_role_row("HOD", hod_user_id)
            dept = get_or_create_department(dept_name, dept_desc, hod.hod_id)
            departments.append((dept, hod))

        # ----------------------------
        # 3) Reviewers (shared pool)
        # ----------------------------
        reviewers = []
        for i in range(4):
            reviewer_user_id = get_or_create_user_id(
                email=f"reviewer{i+1}@gmail.com",
                full_name=f"Reviewer {i+1}",
                role="REVIEWER",
                password_plain="demo",
                account_status="ACTIVE"
            )
            reviewers.append(ensure_role_row("REVIEWER", reviewer_user_id))

        # ----------------------------
        # 4) Proposals per department
        #    - 2 PENDING (no FinalDecision) -> should show in Final Approval list
        #    - 1 APPROVED (FinalDecision exists)
        #    - 1 REJECTED (FinalDecision exists)
        # ----------------------------
        title_bank = {
            "Computer Science": [
                ("AI Phishing Detection Using Email Metadata", 14000, None),              # PENDING
                ("Smart Campus Energy Optimization Using IoT", 15000, None),              # PENDING
                ("Early Warning Flood Risk Prediction (Pilot)", 12000, "APPROVED"),       # DECIDED
                ("Blockchain Certificate Verification (Large)", 28000, "REJECTED"),      # DECIDED
            ],
            "Engineering": [
                ("Low-Cost Structural Health Monitoring Sensors", 13000, None),
                ("Energy-Efficient HVAC Optimization in Buildings", 14500, None),
                ("Bridge Vibration Analytics (Phase 1)", 12000, "APPROVED"),
                ("Autonomous Drone Inspection for Factories", 35000, "REJECTED"),
            ],
            "Business": [
                ("SME Cashflow Forecasting Using Explainable AI", 11000, None),
                ("Retail Customer Churn Prediction Dashboard", 15000, None),
                ("Digital Payment Fraud Screening (Prototype)", 12000, "APPROVED"),
                ("Blockchain Loyalty Rewards Marketplace", 26000, "REJECTED"),
            ],
            "Management": [
                ("University Grant Risk Analytics Dashboard", 9000, None),
                ("Multi-Criteria Resource Allocation Optimizer", 14000, None),
                ("Project Portfolio Tracking (Pilot)", 12000, "APPROVED"),
                ("Organizational Change Impact Study", 22000, "REJECTED"),
            ],
            "Multimedia": [
                ("Interactive AR Campus Navigation Guide", 15000, None),
                ("Gamified Mental Health Support Micro-Learning", 12500, None),
                ("AR Onboarding for New Students (Pilot)", 12000, "APPROVED"),
                ("VR Emergency Response Training Suite", 40000, "REJECTED"),
            ],
        }

        researcher_counter = 1

        for dept, hod in departments:
            scheme = get_or_create_scheme_for_department(
                admin_id=admin.admin_id,
                dept_id=dept.department_id,
                dept_name=dept.department_name
            )

            for (base_title, budget, decision) in title_bank[dept.department_name]:
                # Make titles unique across departments (prevents “same thing” duplicates)
                title = f"{base_title} ({dept.department_name})"

                # Create researcher
                email = f"researcher{researcher_counter}@gmail.com"
                researcher_user_id = get_or_create_user_id(
                    email=email,
                    full_name=f"Researcher {researcher_counter}",
                    role="RESEARCHER",
                    password_plain="demo",
                    account_status="ACTIVE"
                )
                researcher_counter += 1
                researcher = ensure_role_row("RESEARCHER", researcher_user_id)

                # Create proposal if not exists
                proposal = Proposal.query.filter_by(project_title=title).first()
                if not proposal:
                    proposal = Proposal(
                        proposal_id=uid(),
                        scheme_id=scheme.scheme_id,
                        researcher_id=researcher.researcher_id,
                        project_title=title,
                        abstract="Demo abstract for FINAL APPROVAL testing.",
                        methodology="Demo methodology section for FINAL APPROVAL testing.",
                        requested_budget=budget,
                        submission_date=datetime.now(timezone.utc),
                        proposal_status="SUBMITTED"
                    )
                    db.session.add(proposal)
                    db.session.commit()

                # Ensure pipeline exists (reviews + endorsement)
                ensure_review_pipeline(proposal, reviewers, budget, hod.hod_id)

                # Final decision setup:
                # None => PENDING (remove FinalDecision if exists)
                # "APPROVED"/"REJECTED" => ensure exists
                set_final_decision(proposal.proposal_id, admin.admin_id, decision)

        print("✅ Demo data seeded successfully for FINAL APPROVAL page!")
        print("✅ Admin login: admin_demo@gmail.com / 1234")
        print("✅ Final Approval page should show PENDING proposals (no FinalDecision).")
        print("✅ There are also APPROVED/REJECTED proposals for extra testing.")

if __name__ == "__main__":
    run()
