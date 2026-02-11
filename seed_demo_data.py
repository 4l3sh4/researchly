
from __future__ import annotations
from datetime import datetime, timezone, date, timedelta
import uuid

from main import (
    app, db, bcrypt,
    User, UserProfile,
    Admin, Reviewer, Researcher,
    Department, GrantScheme, Proposal,
    ReviewersAssignment, Review,
    FinalDecision,
    Project, FundingAllocation,
    ProgressReport
)

def uid():
    return str(uuid.uuid4())

def now():
    return datetime.now(timezone.utc)

def hash_pw(pw):
    return bcrypt.generate_password_hash(pw).decode("utf-8")

def create_user(email, name, password, role, department=None):
    user = User(id=uid(), full_name=name, email=email, password=hash_pw(password))
    db.session.add(user)
    db.session.commit()

    profile = UserProfile(
        user_id=user.id,
        role=role,
        account_status="ACTIVE",
        department_name=department
    )
    db.session.add(profile)
    db.session.commit()

    if role == "ADMIN":
        db.session.add(Admin(admin_id=uid(), user_id=user.id))
    elif role == "REVIEWER":
        db.session.add(Reviewer(reviewer_id=uid(), user_id=user.id))
    elif role == "RESEARCHER":
        db.session.add(Researcher(researcher_id=uid(), user_id=user.id))

    db.session.commit()
    return user


def run():
    with app.app_context():

        db.drop_all()
        db.create_all()

        # ---------------- USERS ----------------

        create_user("admin@researchly.demo", "System Admin", "1234", "ADMIN")
        create_user("reviewer@researchly.demo", "Daniel Ong", "demo123", "REVIEWER", "Computer Science")
        create_user("aisyah@researchly.demo", "Aisyah Rahman", "demo123", "RESEARCHER", "Computer Science")

        admin_row = Admin.query.first()
        reviewer_row = Reviewer.query.first()
        researcher_row = Researcher.query.first()

        # ---------------- DEPARTMENT ----------------

        dept = Department(
            department_id=uid(),
            department_name="Computer Science",
            department_description="AI and Systems Research"
        )
        db.session.add(dept)
        db.session.commit()

        # ---------------- GRANT SCHEME ----------------

        scheme = GrantScheme(
            scheme_id=uid(),
            admin_id=admin_row.admin_id,
            department_id=dept.department_id,
            description="2026 Open Research Grant",
            eligibiliity="All academic staff",
            open_date=date.today() - timedelta(days=10),
            close_date=date.today() + timedelta(days=30),
            max_budget=50000,
            project_duration_limit=12,
            required_documents="Proposal + Budget",
            reporting_requirements="Midterm + Final",
            scheme_status="OPEN"
        )
        db.session.add(scheme)
        db.session.commit()

        # =====================================================
        # SUBMITTED
        # =====================================================

        p_submitted = Proposal(
            proposal_id=uid(),
            scheme_id=scheme.scheme_id,
            researcher_id=researcher_row.researcher_id,
            project_title="AI Grant Evaluation System",
            abstract="Automating evaluation using AI",
            methodology="Prototype + Testing",
            requested_budget=20000,
            submission_date=now(),
            proposal_status="SUBMITTED"
        )
        db.session.add(p_submitted)

        # =====================================================
        #  UNDER REVIEW (ASSIGNED BUT NOT DECIDED)
        # =====================================================

        p_under_review = Proposal(
            proposal_id=uid(),
            scheme_id=scheme.scheme_id,
            researcher_id=researcher_row.researcher_id,
            project_title="Secure Research Data Vault",
            abstract="Encrypted storage for research",
            methodology="Security testing",
            requested_budget=25000,
            submission_date=now(),
            proposal_status="UNDER REVIEW"
        )
        db.session.add(p_under_review)
        db.session.commit()

        db.session.add(ReviewersAssignment(
            assignment_id=uid(),
            proposal_id=p_under_review.proposal_id,
            reviewer_id=reviewer_row.reviewer_id,
            assigned_date=now(),
            assignment_status="ASSIGNED"
        ))

        # =====================================================
        #  READY FOR FINAL DECISION (REVIEW COMPLETE, NO FINAL DECISION)
        # =====================================================

        p_ready_decision = Proposal(
            proposal_id=uid(),
            scheme_id=scheme.scheme_id,
            researcher_id=researcher_row.researcher_id,
            project_title="Smart Campus Energy Optimization",
            abstract="AI energy monitoring",
            methodology="Sensor + Analytics",
            requested_budget=24000,
            submission_date=now(),
            proposal_status="UNDER REVIEW"
        )
        db.session.add(p_ready_decision)
        db.session.commit()

        db.session.add(ReviewersAssignment(
            assignment_id=uid(),
            proposal_id=p_ready_decision.proposal_id,
            reviewer_id=reviewer_row.reviewer_id,
            assigned_date=now(),
            assignment_status="COMPLETED"
        ))

        db.session.add(Review(
            review_id=uid(),
            proposal_id=p_ready_decision.proposal_id,
            reviewer_id=reviewer_row.reviewer_id,
            review_date=now(),
            recommendation="APPROVE",
            feedback="Technically strong and feasible project."
        ))

        # =====================================================
        #  REVISION REQUIRED
        # =====================================================

        p_revision = Proposal(
            proposal_id=uid(),
            scheme_id=scheme.scheme_id,
            researcher_id=researcher_row.researcher_id,
            project_title="Campus Drone Monitoring",
            abstract="Drone monitoring system",
            methodology="Deploy 15 drones",
            requested_budget=80000,
            submission_date=now(),
            proposal_status="REVISION REQUIRED"
        )
        db.session.add(p_revision)
        db.session.commit()

        db.session.add(Review(
            review_id=uid(),
            proposal_id=p_revision.proposal_id,
            reviewer_id=reviewer_row.reviewer_id,
            review_date=now(),
            recommendation="REVISION REQUIRED",
            feedback="Budget too high. Reduce drone quantity."
        ))

        # =====================================================
        #  REJECTED
        # =====================================================

        p_rejected = Proposal(
            proposal_id=uid(),
            scheme_id=scheme.scheme_id,
            researcher_id=researcher_row.researcher_id,
            project_title="Blockchain Lab Setup",
            abstract="Blockchain infrastructure",
            methodology="Full lab setup",
            requested_budget=120000,
            submission_date=now(),
            proposal_status="REJECTED"
        )
        db.session.add(p_rejected)
        db.session.commit()

        db.session.add(FinalDecision(
            final_decision_id=uid(),
            proposal_id=p_rejected.proposal_id,
            admin_id=admin_row.admin_id,
            decision="REJECTED",
            decision_date=now()
        ))

        # =====================================================
        #  APPROVED (NO ALLOCATION)
        # =====================================================

        p_no_alloc = Proposal(
            proposal_id=uid(),
            scheme_id=scheme.scheme_id,
            researcher_id=researcher_row.researcher_id,
            project_title="AI Ethics Monitoring",
            abstract="Ethics compliance monitoring",
            methodology="Policy engine",
            requested_budget=18000,
            submission_date=now(),
            proposal_status="APPROVED"
        )
        db.session.add(p_no_alloc)
        db.session.commit()

        db.session.add(FinalDecision(
            final_decision_id=uid(),
            proposal_id=p_no_alloc.proposal_id,
            admin_id=admin_row.admin_id,
            decision="APPROVED",
            decision_date=now()
        ))

        # =====================================================
        #  APPROVED (DRAFT ALLOCATION)
        # =====================================================

        p_draft = Proposal(
            proposal_id=uid(),
            scheme_id=scheme.scheme_id,
            researcher_id=researcher_row.researcher_id,
            project_title="Research Analytics Tool",
            abstract="Analytics dashboard",
            methodology="Flask + Charts",
            requested_budget=22000,
            submission_date=now(),
            proposal_status="APPROVED"
        )
        db.session.add(p_draft)
        db.session.commit()

        db.session.add(FinalDecision(
            final_decision_id=uid(),
            proposal_id=p_draft.proposal_id,
            admin_id=admin_row.admin_id,
            decision="APPROVED",
            decision_date=now()
        ))

        project_draft = Project(
            project_id=uid(),
            proposal_id=p_draft.proposal_id,
            researcher_id=researcher_row.researcher_id,
            scheme_id=scheme.scheme_id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=120),
            project_status="NOT STARTED"
        )
        db.session.add(project_draft)
        db.session.commit()

        db.session.add(FundingAllocation(
            allocation_id=uid(),
            admin_id=admin_row.admin_id,
            project_id=project_draft.project_id,
            total_amount=22000,
            equipment_amount=8000,
            materials_amount=5000,
            travel_amount=4000,
            other_amount=5000,
            allocation_date=now(),
            allocation_status="DRAFT"
        ))

        # =====================================================
        #  APPROVED (CONFIRMED + PROJECT + PROGRESS)
        # =====================================================

        p_confirmed = Proposal(
            proposal_id=uid(),
            scheme_id=scheme.scheme_id,
            researcher_id=researcher_row.researcher_id,
            project_title="Automated Reporting Dashboard",
            abstract="Research tracking system",
            methodology="Flask + Analytics",
            requested_budget=20000,
            submission_date=now(),
            proposal_status="APPROVED"
        )
        db.session.add(p_confirmed)
        db.session.commit()

        db.session.add(FinalDecision(
            final_decision_id=uid(),
            proposal_id=p_confirmed.proposal_id,
            admin_id=admin_row.admin_id,
            decision="APPROVED",
            decision_date=now()
        ))

        project = Project(
            project_id=uid(),
            proposal_id=p_confirmed.proposal_id,
            researcher_id=researcher_row.researcher_id,
            scheme_id=scheme.scheme_id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=180),
            project_status="IN PROGRESS"
        )
        db.session.add(project)
        db.session.commit()

        db.session.add(FundingAllocation(
            allocation_id=uid(),
            admin_id=admin_row.admin_id,
            project_id=project.project_id,
            total_amount=20000,
            equipment_amount=7000,
            materials_amount=5000,
            travel_amount=3000,
            other_amount=5000,
            allocation_date=now(),
            allocation_status="CONFIRMED"
        ))

        db.session.add(ProgressReport(
            progress_id=uid(),
            project_id=project.project_id,
            researcher_id=researcher_row.researcher_id,
            period_start_date=date.today() - timedelta(days=60),
            period_end_date=date.today(),
            summary="Milestone 1 completed.",
            milestones_achieved="Prototype ready",
            challenges="Minor UI issue",
            resource_usage="Within budget",
            submission_date=now(),
            status="UNDER REVIEW",
            hod_comments="Good progress."
        ))

        db.session.commit()

        print("Demo data seeded successfully.")
        print("Admin: admin@researchly.demo / 1234")
        print("Researcher: aisyah@researchly.demo / demo123")
        print("Reviewer: reviewer@researchly.demo / demo123")


if __name__ == "__main__":
    run()
