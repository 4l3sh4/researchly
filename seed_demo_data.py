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
    Returns user_id (string) only - avoids SQLAlchemy expired-object issues.
    Also ensures UserProfile exists.
    """
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(
            id=uid(),
            full_name=full_name,
            email=email,
            password=hash_pw(password_plain)
        )
        db.session.add(u)
        db.session.add(UserProfile(user_id=u.id, role=role, account_status=account_status))
        db.session.commit()
        return u.id

    # ensure profile exists / updated
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
    """
    Department has fields:
      - department_id
      - hod_id
      - department_name
      - department_description
    """
    dept = Department.query.filter_by(department_name=dept_name).first()
    if dept:
        # if a different hod_id, keep existing (or update if you want)
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
    """
    Create 1 OPEN scheme per department (unique by description).
    """
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

# -------------------------
# Seeder
# -------------------------
def run():
    with app.app_context():
        db.create_all()

        # Optional extra stability
        # db.session.expire_on_commit = False

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
        for i, (dept_name, dept_desc) in enumerate(dept_specs, start=1):
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
        for i in range(3):
            reviewer_user_id = get_or_create_user_id(
                email=f"reviewer{i+1}@gmail.com",
                full_name=f"Reviewer {i+1}",
                role="REVIEWER",
                password_plain="demo",
                account_status="ACTIVE"
            )
            reviewers.append(ensure_role_row("REVIEWER", reviewer_user_id))

        # ----------------------------
        # 4) Create schemes + proposals across departments
        #    Per department:
        #      - 2 approved (<=15000) -> should appear in Funding Allocation
        #      - 1 rejected (>15000)  -> should NOT appear
        # ----------------------------
        title_bank = {
            "Computer Science": [
                ("AI-Based Early Warning System for Flood Risk Prediction", 12000, "APPROVED"),
                ("Smart Campus Energy Optimization Using IoT Sensors", 15000, "APPROVED"),
                ("Blockchain-Based Certificate Verification Platform", 28000, "REJECTED"),
            ],
            "Engineering": [
                ("Low-Cost Structural Health Monitoring with Edge Sensors", 13000, "APPROVED"),
                ("Energy-Efficient HVAC Optimization in Smart Buildings", 14500, "APPROVED"),
                ("Autonomous Drone Inspection for Industrial Facilities", 35000, "REJECTED"),
            ],
            "Business": [
                ("SME Cashflow Forecasting Using Explainable AI", 11000, "APPROVED"),
                ("Customer Churn Prediction for Subscription Services", 15000, "APPROVED"),
                ("Blockchain-Based Loyalty Rewards Marketplace", 26000, "REJECTED"),
            ],
            "Management": [
                ("Project Risk Analytics Dashboard for University Grants", 9000, "APPROVED"),
                ("Optimizing Resource Allocation with Multi-Criteria Decision Making", 14000, "APPROVED"),
                ("Large-Scale Organizational Change Impact Study", 22000, "REJECTED"),
            ],
            "Multimedia": [
                ("Interactive AR Orientation Guide for Campus Navigation", 15000, "APPROVED"),
                ("Gamified Mental Health Support Micro-Learning App", 12500, "APPROVED"),
                ("Full-Scale VR Training Suite for Emergency Response", 40000, "REJECTED"),
            ],
        }

        researcher_counter = 1

        for dept, hod in departments:
            scheme = get_or_create_scheme_for_department(
                admin_id=admin.admin_id,
                dept_id=dept.department_id,
                dept_name=dept.department_name
            )

            for (base_title, budget, final_decision) in title_bank[dept.department_name]:
                # unique title per dept to avoid duplicates + help filter testing
                title = base_title

                # researcher for each proposal
                email = f"researcher{researcher_counter}@gmail.com"
                researcher_counter += 1

                researcher_user_id = get_or_create_user_id(
                    email=email,
                    full_name=f"Researcher {researcher_counter}",
                    role="RESEARCHER",
                    password_plain="demo",
                    account_status="ACTIVE"
                )
                researcher = ensure_role_row("RESEARCHER", researcher_user_id)

                # avoid duplicate proposals if re-run
                proposal = Proposal.query.filter_by(project_title=title).first()
                if not proposal:
                    proposal = Proposal(
                        proposal_id=uid(),
                        scheme_id=scheme.scheme_id,
                        researcher_id=researcher.researcher_id,
                        project_title=title,
                        abstract="Demo abstract for funding allocation testing.",
                        methodology="Demo methodology section.",
                        requested_budget=budget,
                        submission_date=datetime.now(timezone.utc),
                        proposal_status="SUBMITTED"
                    )
                    db.session.add(proposal)
                    db.session.commit()

                # Assign reviewers + create reviews
                for rv in reviewers[:2]:  # assign 2 reviewers
                    if not ReviewersAssignment.query.filter_by(
                        proposal_id=proposal.proposal_id,
                        reviewer_id=rv.reviewer_id
                    ).first():
                        db.session.add(ReviewersAssignment(
                            assignment_id=uid(),
                            proposal_id=proposal.proposal_id,
                            reviewer_id=rv.reviewer_id,
                            assignment_status="ASSIGNED"
                        ))

                    if not Review.query.filter_by(
                        proposal_id=proposal.proposal_id,
                        reviewer_id=rv.reviewer_id
                    ).first():
                        db.session.add(Review(
                            review_id=uid(),
                            proposal_id=proposal.proposal_id,
                            reviewer_id=rv.reviewer_id,
                            review_date=datetime.now(timezone.utc),
                            recommendation="APPROVE" if budget <= 15000 else "REVISE",
                            feedback="Demo feedback for testing."
                        ))

                # HOD endorsement (for that dept's hod)
                if not HODEndorsement.query.filter_by(proposal_id=proposal.proposal_id).first():
                    db.session.add(HODEndorsement(
                        hod_endorsement_id=uid(),
                        hod_id=hod.hod_id,
                        proposal_id=proposal.proposal_id,
                        decision="ENDORSE",
                        remarks="Endorsed for demo testing."
                    ))

                # Admin final decision (APPROVED/REJECTED)
                existing_final = FinalDecision.query.filter_by(proposal_id=proposal.proposal_id).first()
                if not existing_final:
                    db.session.add(FinalDecision(
                        final_decision_id=uid(),
                        proposal_id=proposal.proposal_id,
                        admin_id=admin.admin_id,
                        decision=final_decision
                    ))

                db.session.commit()

        # ----------------------------
        # METHOD 1 IMPORTANT:
        # Do NOT create Project or FundingAllocation here.
        # Funding Allocation pages should create those.
        # ----------------------------
        print("✅ Demo data seeded successfully!")
        print("✅ Admin login: admin_demo@gmail.com / 1234")
        print("✅ Funding Allocation test: use department filter (ALL, CS, Engineering, Business, Management, Multimedia)")
        print("✅ Only APPROVED proposals exist per department for the funding allocation list (plus REJECTED for other testing).")

if __name__ == "__main__":
    run()
