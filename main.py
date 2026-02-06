from flask import Flask, render_template, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from datetime import datetime, timezone
from flask import request, abort, flash
from functools import wraps
from werkzeug.utils import secure_filename
from sqlalchemy import func
import uuid
import os

DISPLAY_STATUS_OPTIONS = [
    "Pending Assignment",
    "Pending Review",
    "Pending Endorsement",
    "Pending Approval",
    "Pending Funding",
    "Approved",
    "Rejected",
    "Funded",
]

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'A&WGirlies'

app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB limit
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(db.Model, UserMixin):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)

class UserProfile(db.Model):
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), primary_key=True)

    contact_number = db.Column(db.String(15), nullable=True)         
    address = db.Column(db.String(100), nullable=True)                
    emergency_contact_name = db.Column(db.String(80), nullable=True)  
    emergency_contact_number = db.Column(db.String(15), nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    department_name = db.Column(db.String(80), nullable=True)
    expertise_tags = db.Column(db.String(255), nullable=True)

    role = db.Column(db.String(20), nullable=False, default="UNASSIGNED")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    account_status = db.Column(db.String(15), nullable=False)

class BankAccount(db.Model):
    bank_account_number = db.Column(db.String(34), primary_key=True)
    bank_name = db.Column(db.String(100), nullable=False)

class Admin(db.Model):
    admin_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36),
        db.ForeignKey('user.id')
    )

class HOD(db.Model):
    hod_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36),
        db.ForeignKey('user.id')
    )

class Reviewer(db.Model):
    reviewer_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36),
        db.ForeignKey('user.id')
    )

class Researcher(db.Model):
    researcher_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36),
        db.ForeignKey('user.id')
    )
    bank_account_number = db.Column(
        db.String(34),
        db.ForeignKey('bank_account.bank_account_number')
    )

class Department(db.Model):
    department_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hod_id = db.Column(
        db.String(36),
        db.ForeignKey('hod.hod_id')
    )
    department_name = db.Column(db.String(50), nullable=False)
    department_description = db.Column(db.String(500), nullable=False)

class GrantScheme(db.Model):
    scheme_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = db.Column(
        db.String(36),
        db.ForeignKey('admin.admin_id'),
    )
    department_id = db.Column(
        db.String(36),
        db.ForeignKey('department.department_id'),
    )
    description = db.Column(db.String(500), nullable=False)
    eligibiliity = db.Column(db.String(500), nullable=False)
    open_date = db.Column(db.Date, nullable=False)
    close_date = db.Column(db.Date, nullable=False)
    max_budget = db.Column(db.Integer, nullable=False)
    project_duration_limit = db.Column(db.Integer, nullable=False)
    required_documents = db.Column(db.String(500), nullable=False)
    reporting_requirements = db.Column(db.String(500), nullable=False)
    scheme_status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc), onupdate=lambda:datetime.now(timezone.utc), nullable=False)

class Proposal(db.Model):
    proposal_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_id = db.Column(
        db.String(36),
        db.ForeignKey('grant_scheme.scheme_id'),
    )
    researcher_id = db.Column(
        db.String(36),
        db.ForeignKey('researcher.researcher_id'),
    )
    project_title = db.Column(db.String(100), nullable=False)
    abstract = db.Column(db.String(500), nullable=False)
    methodology = db.Column(db.String(500), nullable=False)
    requested_budget = db.Column(db.Integer, nullable=False)
    submission_date = db.Column(db.DateTime, nullable=False)
    proposal_status = db.Column(db.String(15), nullable=False)

class Review(db.Model):
    review_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proposal_id = db.Column(
        db.String(36),
        db.ForeignKey('proposal.proposal_id'),
    )
    reviewer_id = db.Column(
        db.String(36),
        db.ForeignKey('reviewer.reviewer_id'),
    )
    review_date = db.Column(db.DateTime, nullable=False)
    recommendation = db.Column(db.String(20), nullable=False)
    feedback = db.Column(db.String(500), nullable=False)

class ReviewersAssignment(db.Model):
    assignment_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proposal_id = db.Column(
        db.String(36),
        db.ForeignKey('proposal.proposal_id'),
    )
    reviewer_id = db.Column(
        db.String(36),
        db.ForeignKey('reviewer.reviewer_id'),
    )
    assigned_date = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    assignment_status = db.Column(db.String(15), nullable=False)

class HODEndorsement(db.Model):
    hod_endorsement_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hod_id = db.Column(
        db.String(36),
        db.ForeignKey('hod.hod_id'),
    )
    proposal_id = db.Column(
        db.String(36),
        db.ForeignKey('proposal.proposal_id'),
    )
    decision = db.Column(db.String(20), nullable=False)
    decision_date = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    remarks = db.Column(db.String(500), nullable=False)

class FinalDecision(db.Model):
    final_decision_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proposal_id = db.Column(
        db.String(36),
        db.ForeignKey('proposal.proposal_id'),
    )
    admin_id = db.Column(
        db.String(36),
        db.ForeignKey('admin.admin_id'),
    )
    decision = db.Column(db.String(15), nullable=False)
    decision_date = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)

class Project(db.Model):
    project_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proposal_id = db.Column(
        db.String(36),
        db.ForeignKey('proposal.proposal_id'),
    )
    researcher_id = db.Column(
        db.String(36),
        db.ForeignKey('researcher.researcher_id'),
    )
    scheme_id = db.Column(
        db.String(36),
        db.ForeignKey('grant_scheme.scheme_id'),
    )
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    project_status = db.Column(db.String(15), nullable=False)

class FundingAllocation(db.Model):
    allocation_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = db.Column(
        db.String(36),
        db.ForeignKey('admin.admin_id'),
    )
    project_id = db.Column(
        db.String(36),
        db.ForeignKey('project.project_id'),
    )
    total_amount = db.Column(db.Integer, nullable=False)
    equipment_amount = db.Column(db.Integer, nullable=False)
    materials_amount = db.Column(db.Integer, nullable=False)
    travel_amount = db.Column(db.Integer, nullable=False)
    other_amount = db.Column(db.Integer, nullable=False)
    allocation_date = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    allocation_status = db.Column(db.String(20), nullable=False)

class ProgressReport(db.Model):
    progress_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(
        db.String(36),
        db.ForeignKey('project.project_id'),
    )
    researcher_id = db.Column(
        db.String(36),
        db.ForeignKey('researcher.researcher_id'),
    )
    hod_id = db.Column(
        db.String(36),
        db.ForeignKey('hod.hod_id'),
    )
    period_start_date = db.Column(db.Date, nullable=False)
    period_end_date = db.Column(db.Date, nullable=False)
    summary = db.Column(db.String(500), nullable=False)
    milestones_achieved = db.Column(db.String(500), nullable=False)
    challenges = db.Column(db.String(500), nullable=False)
    resource_usage = db.Column(db.String(500), nullable=False)
    submission_date = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    hod_comments = db.Column(db.String(500), nullable=False)

class Notification(db.Model):
    notification_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36),
        db.ForeignKey('user.id'),
    )
    message = db.Column(db.String(100), nullable=False)
    notif_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    # Flask-Login uses this to reload the user from the session
    return User.query.get(user_id)


class RegisterForm(FlaskForm):
    email = StringField(validators=[InputRequired(), Length(min=4, max=255)], render_kw={"placeholder": "Email"})
    full_name = StringField(validators=[InputRequired(), Length(min=4, max=80)], render_kw={"placeholder": "Full Name"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=50)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")

    def validate_email(self, email):
        existing_user_email = User.query.filter_by(email=email.data).first()
        if existing_user_email:
            raise ValidationError("This email is already in use. Please type in the correct one or retry your password.")


class LoginForm(FlaskForm):
    email = StringField(validators=[InputRequired(), Length(min=4, max=255)], render_kw={"placeholder": "Email"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=50)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")

def profile_needs_setup(prof) -> bool:
    """True if user must complete profile before accessing dashboard."""
    if not prof:
        return True

    # Fields EVERYONE must fill (adjust as you like)
    required = [
        prof.contact_number,
        prof.address,
        prof.emergency_contact_name,
        prof.emergency_contact_number,
    ]
    if any(not (v or "").strip() for v in required):
        return True

    # Non-admin should also fill department
    if prof.role != "ADMIN" and not (prof.department_name or "").strip():
        return True

    # Reviewer should also fill expertise tags (if you use it)
    if prof.role == "REVIEWER" and not (getattr(prof, "expertise_tags", "") or "").strip():
        return True

    return False

def get_profile(user_id: str):
    return UserProfile.query.filter_by(user_id=user_id).first()

def get_researcher(user_id: str):
    return Researcher.query.filter_by(user_id=user_id).first()

def get_bank_account(bank_account_number: str):
    if not bank_account_number:
        return None
    return BankAccount.query.filter_by(bank_account_number=bank_account_number).first()

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def is_admin_user(user: User) -> bool:
    prof = get_profile(user.id)
    return bool(prof and prof.account_status == "ACTIVE" and prof.role == "ADMIN")

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not is_admin_user(current_user):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def get_admin_by_user(user_id: str):
    return Admin.query.filter_by(user_id=user_id).first()

def parse_date_yyyy_mm_dd(value: str):
    if not value:
        return None
    # HTML <input type="date"> sends YYYY-MM-DD
    return datetime.strptime(value, "%Y-%m-%d").date()

def compute_reviewer_recommendation(proposal_id: str) -> str:
    reviews = Review.query.filter_by(proposal_id=proposal_id).all()
    if not reviews:
        return "Pending"

    approve = sum(1 for r in reviews if (r.recommendation or "").upper() == "APPROVE")
    other = len(reviews) - approve
    return "Recommended" if approve >= other else "Not Recommended"

from flask import abort

def get_or_404(model, pk):
    obj = db.session.get(model, pk)
    if not obj:
        abort(404)
    return obj

@app.context_processor
def inject_profile():
    if current_user.is_authenticated:
        return {"prof": get_profile(current_user.id)}
    return {"prof": None}

from typing import Union

def compute_proposal_display_status(p_or_id: Union["Proposal", str]) -> str:
    # Accept either Proposal object or proposal_id string
    if isinstance(p_or_id, str):
        p = db.session.get(p_or_id)
        if not p:
            return "Unknown"
    else:
        p = p_or_id

    pid = p.proposal_id

    # 1) If proposal_status already stores an end-state, trust it
    st = (p.proposal_status or "").upper().strip()
    if st in {"FUNDED", "REJECTED"}:
        return st.title()  # Funded / Rejected

    # 2) Funding confirmed? (Project + FundingAllocation exists)
    project = Project.query.filter_by(proposal_id=pid).first()
    if project:
        alloc = FundingAllocation.query.filter_by(project_id=project.project_id).first()
        if alloc and (alloc.allocation_status or "").upper() == "CONFIRMED":
            return "Funded"

    # 3) Final decision exists?
    final = FinalDecision.query.filter_by(proposal_id=pid).first()
    if final:
        if (final.decision or "").upper() == "APPROVED":
            return "Pending Funding"
        return "Rejected"

    # 4) HoD endorsement exists?
    hod = HODEndorsement.query.filter_by(proposal_id=pid).first()
    if hod:
        if (hod.decision or "").upper() == "ENDORSE":
            return "Pending Approval"
        return "Rejected"

    # 5) Reviewer assignments exist?
    assignments = ReviewersAssignment.query.filter_by(proposal_id=pid).all()
    if not assignments:
        return "Pending Assignment"

    # 6) Reviews progress
    reviews = Review.query.filter_by(proposal_id=pid).all()
    if not reviews:
        return "Pending Review"

    if len(reviews) >= len(assignments):
        return "Pending Endorsement"

    return "Pending Review"

@app.route("/")
def home():
    return redirect(url_for("register"))

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     form = LoginForm()
#     error_message = None

#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()

#         if user and bcrypt.check_password_hash(user.password, form.password.data):
#             prof = get_profile(user.id)

#             if not prof:
#                 error_message = "Profile not found. Please contact admin."
#             elif prof.account_status != "ACTIVE":
#                 error_message = "Your account is not active yet. Please wait for admin approval."
#             else:
#                 login_user(user)

#                 # Force complete profile first (ALL roles)
#                 if profile_needs_setup(prof):
#                     flash("Please complete your profile before continuing.", "info")
#                     return redirect(url_for("edit_profile"))

#                 # then normal routing
#                 if prof.role == "ADMIN":
#                     return redirect(url_for("admin_users"))
#                 return redirect(url_for("dashboard"))
#         else:
#             error_message = "Invalid email or password. Please try again."

#     return render_template('login.html', form=form, error_message=error_message)

# Temporary to allow seed_demo_data.py
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    error_message = None

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        # Accept BOTH bcrypt-hash passwords and plain-text demo passwords
        ok = False
        if user:
            try:
                ok = bcrypt.check_password_hash(user.password, form.password.data)
            except ValueError:
                # stored password is not a bcrypt hash (e.g. "demo")
                ok = (user.password == form.password.data)

        if user and ok:
            prof = get_profile(user.id)

            if not prof:
                error_message = "Profile not found. Please contact admin."
            elif prof.account_status != "ACTIVE":
                error_message = "Your account is not active yet. Please wait for admin approval."
            else:
                login_user(user)
                
                # Force complete profile first (ALL roles)
                if profile_needs_setup(prof):
                    flash("Please complete your profile before continuing.", "info")
                    return redirect(url_for("edit_profile"))

                # then normal routing
                if prof.role == "ADMIN":
                    return redirect(url_for("admin_users"))
                return redirect(url_for("dashboard"))
        else:
            error_message = "Invalid email or password. Please try again."

    return render_template('login.html', form=form, error_message=error_message)

@app.route("/dashboard")
@login_required
def dashboard():
    prof = get_profile(current_user.id)

    # If profile missing, treat as pending (or block)
    if not prof:
        return render_template("dashboard.html")

    # Pending / Deactivated -> show the existing pending template
    if prof.account_status != "ACTIVE":
        return render_template("dashboard.html")  # your pending page

    # Admin -> go to admin dashboard
    if prof.role == "ADMIN":
        return redirect(url_for("admin_dashboard"))

    # Others -> normal dashboard (for now reuse the same template or create user_dashboard.html later)
    return render_template("dashboard.html")

@app.route("/profile")
@login_required
def view_profile():
    prof = get_profile(current_user.id)
    if not prof:
        flash("Profile not found. Please contact admin.", "error")
        return redirect(url_for("dashboard"))

    researcher = get_researcher(current_user.id)
    bank = get_bank_account(researcher.bank_account_number) if researcher else None

    return render_template(
        "view_profile.html",
        user=current_user,
        prof=prof,
        researcher=researcher,
        bank=bank
    )

@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    prof = get_profile(current_user.id)
    if not prof:
        abort(404)

    if request.method == "POST":
        # basic fields (shared for all roles)
        current_user.full_name = (request.form.get("full_name") or "").strip()

        prof.contact_number = (request.form.get("contact_number") or "").strip()
        prof.address = (request.form.get("address") or "").strip()
        prof.emergency_contact_name = (request.form.get("emergency_contact_name") or "").strip()
        prof.emergency_contact_number = (request.form.get("emergency_contact_number") or "").strip()

        # department: only for non-admin
        if prof.role != "ADMIN":
            prof.department_name = (request.form.get("department_name") or "").strip()
        else:
            prof.department_name = None

        # profile picture upload
        file = request.files.get("profile_picture")
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Invalid file type. Please upload PNG/JPG/JPEG/GIF only.", "error")
                return redirect(url_for("edit_profile"))

            ext = file.filename.rsplit(".", 1)[1].lower()
            filename = secure_filename(f"{current_user.id}.{ext}")  # stable name per user
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            prof.profile_picture = filename

        # bank details: only for researchers
        if prof.role == "RESEARCHER":
            researcher = get_researcher(current_user.id)
            if not researcher:
                researcher = Researcher(user_id=current_user.id)
                db.session.add(researcher)

            bank_acc = (request.form.get("bank_account_number") or "").strip()
            bank_name = (request.form.get("bank_name") or "").strip()

            # If both empty -> remove link (optional behavior)
            if not bank_acc and not bank_name:
                researcher.bank_account_number = None

            # If one filled but not the other -> error
            elif not bank_acc or not bank_name:
                flash("Please fill in BOTH Bank Account Number and Bank Name.", "error")
                return redirect(url_for("edit_profile"))

            else:
                # upsert BankAccount
                bank = BankAccount.query.filter_by(bank_account_number=bank_acc).first()
                if not bank:
                    bank = BankAccount(bank_account_number=bank_acc, bank_name=bank_name)
                    db.session.add(bank)
                else:
                    bank.bank_name = bank_name  # update name if changed

                researcher.bank_account_number = bank_acc

        # Expertise: only for reviewer
        if prof.role == "REVIEWER":
            prof.expertise_tags = (request.form.get("expertise_tags") or "").strip()

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("view_profile"))

    return render_template("edit_profile.html", user=current_user, prof=prof)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        # Check if this is the first user
        is_first_user = (User.query.count() == 0)

        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(email=form.email.data, full_name=form.full_name.data, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        # Create profile immediately
        if is_first_user:
            prof = UserProfile(user_id=new_user.id, role="ADMIN", account_status="ACTIVE")
            db.session.add(prof)

            # Create Admin record too (for your FK relationships)
            db.session.add(Admin(user_id=new_user.id))
            db.session.commit()

            login_user(new_user)
            return redirect(url_for('admin_users'))  # straight to admin panel
        else:
            prof = UserProfile(user_id=new_user.id, role="UNASSIGNED", account_status="PENDING")
            db.session.add(prof)
            db.session.commit()

            # Don’t log them in yet (they are pending)
            flash("Registration submitted. Please wait for admin approval.", "info")
            return redirect(url_for('login'))

    return render_template('register.html', form=form)

#---------------------------------------------------------------------------------------------------------
# ADMIN ROUTES
#---------------------------------------------------------------------------------------------------------

from sqlalchemy import exists, and_, or_
from datetime import datetime

@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    # --- user counts ---
    pending_registrations = UserProfile.query.filter_by(account_status="PENDING").count()
    active_users = UserProfile.query.filter_by(account_status="ACTIVE").count()
    deactivated_users = UserProfile.query.filter_by(account_status="DEACTIVATED").count()

    # --- proposal pipeline counts ---
    proposals = Proposal.query.all()

    pending_reviewer_assignment = 0
    awaiting_hod_decision = 0
    final_approval_needed = 0
    awaiting_budget_allocation = 0
    approved_proposals = 0

    for p in proposals:
        st = compute_proposal_display_status(p)

        if st == "Pending Assignment":
            pending_reviewer_assignment += 1
        elif st == "Pending Endorsement":
            awaiting_hod_decision += 1
        elif st == "Pending Approval":
            final_approval_needed += 1
        elif st == "Approved":
            approved_proposals += 1
            # show on funding list until confirmed funded
            if (p.proposal_status or "").upper() != "FUNDED":
                awaiting_budget_allocation += 1

    # --- grant schemes ---
    active_grant_schemes = GrantScheme.query.filter_by(scheme_status="OPEN").count()

    # --- Recent Activity ---
    recent_activity = []

    # 1) Reviewer assignments
    latest_assignments = (
        ReviewersAssignment.query
        .order_by(ReviewersAssignment.assignment_id.desc())
        .limit(5)
        .all()
    )

    for a in latest_assignments:
        prop = db.session.get(Proposal, a.proposal_id)              # ✅ correct
        rev = db.session.get(Reviewer, a.reviewer_id)               # ✅ correct
        user = db.session.get(User, rev.user_id) if rev else None   # ✅ correct
        if prop and user:
            recent_activity.append(f"Proposal '{prop.project_title}' assigned to {user.full_name}")

    # 2) Final decisions
    latest_decisions = (
        FinalDecision.query
        .order_by(FinalDecision.final_decision_id.desc())
        .limit(5)
        .all()
    )

    for d in latest_decisions:
        prop = db.session.get(Proposal, d.proposal_id)              # ✅ correct
        if prop:
            recent_activity.append(f"Final decision: {d.decision.title()} for '{prop.project_title}'")

    # 3) Funding allocations (FundingAllocation -> Project -> Proposal)
    latest_alloc = (
        FundingAllocation.query
        .order_by(FundingAllocation.allocation_id.desc())
        .limit(5)
        .all()
    )

    for fa in latest_alloc:
        project = db.session.get(Project, fa.project_id)            # ✅ correct
        if not project:
            continue

        prop = db.session.get(Proposal, project.proposal_id)        # ✅ correct
        if not prop:
            continue

        recent_activity.append(f"Budget allocation updated for '{prop.project_title}'")

    recent_activity = recent_activity[:3]

    return render_template(
        "admin_dashboard.html",
        prof=get_profile(current_user.id),

        # tiles
        pending_registrations=pending_registrations,
        pending_reviewer_assignment=pending_reviewer_assignment,
        awaiting_hod_decision=awaiting_hod_decision,
        final_approval_needed=final_approval_needed,
        awaiting_budget_allocation=awaiting_budget_allocation,
        active_grant_schemes=active_grant_schemes,
        approved_proposals=approved_proposals,

        # list
        recent_activity=recent_activity,

        # keep old values (if other templates still use them)
        pending_count=pending_registrations,
        active_count=active_users,
        deactivated_count=deactivated_users,
    )

#------------------
# User Management
#------------------
@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    status = request.args.get("status", "PENDING")   # PENDING / ACTIVE / DEACTIVATED
    q = request.args.get("q", "").strip()

    query = db.session.query(User, UserProfile)\
        .join(UserProfile, User.id == UserProfile.user_id)\
        .filter(UserProfile.account_status == status)

    if q:
        like = f"%{q}%"
        query = query.filter((User.full_name.ilike(like)) | (User.email.ilike(like)))

    rows = query.order_by(UserProfile.created_at.desc()).all()
    return render_template("admin_user_management.html", rows=rows, status=status, q=q)

@app.route("/admin/users/<user_id>/approve", methods=["POST"])
@login_required
@admin_required
def admin_approve_user(user_id):
    role = request.form.get("role", "UNASSIGNED").upper()

    prof = get_profile(user_id)
    if not prof:
        abort(404)

    prof.role = role
    prof.account_status = "ACTIVE"

    # keep role tables consistent
    if role == "ADMIN" and not Admin.query.filter_by(user_id=user_id).first():
        db.session.add(Admin(user_id=user_id))
    if role == "HOD" and not HOD.query.filter_by(user_id=user_id).first():
        db.session.add(HOD(user_id=user_id))
    if role == "REVIEWER" and not Reviewer.query.filter_by(user_id=user_id).first():
        db.session.add(Reviewer(user_id=user_id))
    if role == "RESEARCHER" and not Researcher.query.filter_by(user_id=user_id).first():
        db.session.add(Researcher(user_id=user_id))

    db.session.commit()
    return redirect(url_for("admin_users", status="PENDING"))

@app.route("/admin/users/<user_id>/reject", methods=["POST"])
@login_required
@admin_required
def admin_reject_user(user_id):
    prof = get_profile(user_id)
    if prof:
        db.session.delete(prof)

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)

    db.session.commit()
    return redirect(url_for("admin_users", status="PENDING"))

@app.route("/admin/users/<user_id>/deactivate", methods=["POST"])
@login_required
@admin_required
def admin_deactivate_user(user_id):
    prof = get_profile(user_id)
    if not prof:
        abort(404)
    prof.account_status = "DEACTIVATED"
    db.session.commit()
    return redirect(url_for("admin_users", status="ACTIVE"))

@app.route("/admin/users/<user_id>/activate", methods=["POST"])
@login_required
@admin_required
def admin_activate_user(user_id):
    prof = get_profile(user_id)
    if not prof:
        abort(404)
    prof.account_status = "ACTIVE"
    db.session.commit()
    return redirect(url_for("admin_users", status="DEACTIVATED"))

@app.route("/admin/users/<user_id>/remove", methods=["POST"])
@login_required
@admin_required
def admin_remove_user(user_id):
    prof = get_profile(user_id)
    if prof:
        db.session.delete(prof)

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)

    db.session.commit()
    return redirect(url_for("admin_users", status="DEACTIVATED"))

@app.route("/admin/users/create", methods=["POST"])
@login_required
@admin_required
def admin_create_user():
    full_name = (request.form.get("full_name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    role = (request.form.get("role") or "UNASSIGNED").strip().upper()
    temp_password = (request.form.get("temp_password") or "").strip()

    # basic validation
    if not full_name or not email or not temp_password:
        flash("Full name, email and temporary password are required.", "error")
        return redirect(url_for("admin_users", status="ACTIVE"))

    # prevent duplicates
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Please use another email.", "error")
        return redirect(url_for("admin_users", status="ACTIVE"))

    # hash password
    hashed_pw = bcrypt.generate_password_hash(temp_password).decode("utf-8")

    # create user
    new_user = User(email=email, full_name=full_name, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    # create profile as ACTIVE (since admin is creating manually)
    prof = UserProfile(user_id=new_user.id, role=role, account_status="ACTIVE")
    db.session.add(prof)

    # keep role tables consistent (same idea as admin_approve_user) :contentReference[oaicite:2]{index=2}
    if role == "ADMIN" and not Admin.query.filter_by(user_id=new_user.id).first():
        db.session.add(Admin(user_id=new_user.id))
    if role == "HOD" and not HOD.query.filter_by(user_id=new_user.id).first():
        db.session.add(HOD(user_id=new_user.id))
    if role == "REVIEWER" and not Reviewer.query.filter_by(user_id=new_user.id).first():
        db.session.add(Reviewer(user_id=new_user.id))
    if role == "RESEARCHER" and not Researcher.query.filter_by(user_id=new_user.id).first():
        db.session.add(Researcher(user_id=new_user.id))

    db.session.commit()

    flash(f"User created successfully. Temporary password: {temp_password}", "success")
    return redirect(url_for("admin_users", status="ACTIVE"))

#--------------------------
# Grant Scheme Management
#--------------------------
from datetime import date

@app.route("/admin/grants")
@login_required
@admin_required
def admin_grants():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "ALL").upper()
    prof = get_profile(current_user.id)

    query = db.session.query(GrantScheme, Department)\
        .outerjoin(Department, GrantScheme.department_id == Department.department_id)

    # Search/filter first (optional)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Department.department_name.ilike(like)) |
            (GrantScheme.description.ilike(like))
        )

    from datetime import date

    # auto-close OPEN schemes that already passed close_date
    today = date.today()
    expired = GrantScheme.query.filter(
        db.func.upper(GrantScheme.scheme_status) == "OPEN",
        GrantScheme.close_date < today
    ).all()

    if expired:
        for s in expired:
            s.scheme_status = "CLOSED"
        db.session.commit()

    rows = query.order_by(GrantScheme.created_at.desc()).all()

    # AUTO-CLOSE expired OPEN schemes
    today = date.today()
    changed = False
    for scheme, _dept in rows:
        if (scheme.scheme_status or "").upper() == "OPEN" and scheme.close_date and today > scheme.close_date:
            scheme.scheme_status = "CLOSED"
            changed = True

    if changed:
        db.session.commit()

    # Apply status tab filter AFTER auto-close, so it shows correctly
    if status != "ALL":
        rows = [(s, d) for (s, d) in rows if (s.scheme_status or "").upper() == status]

    return render_template(
        "admin_grant_scheme_management.html",
        rows=rows,
        q=q,
        status=status,
        prof=prof
    )

@app.route("/admin/grants/create", methods=["GET", "POST"])
@login_required
@admin_required
def admin_grant_create():
    prof = get_profile(current_user.id)
    admin = get_admin_by_user(current_user.id)

    # for the datalist suggestions in your HTML
    departments = Department.query.order_by(Department.department_name.asc()).all()

    if not admin:
        flash("Admin record not found for this user.", "error")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        department_name = (request.form.get("department_name") or "").strip()
        description = (request.form.get("description") or "").strip()
        eligibiliity = (request.form.get("eligibiliity") or "").strip()
        required_documents = (request.form.get("required_documents") or "").strip()
        reporting_requirements = (request.form.get("reporting_requirements") or "").strip()

        open_date = parse_date_yyyy_mm_dd(request.form.get("open_date"))
        close_date = parse_date_yyyy_mm_dd(request.form.get("close_date"))

        max_budget = (request.form.get("max_budget") or "").strip()
        project_duration_limit = (request.form.get("project_duration_limit") or "").strip()

        action = (request.form.get("action") or "draft").lower()  # draft / confirm

        # -----------------------------
        # 1) Department: auto-create if missing
        # -----------------------------
        if not department_name:
            flash("Please enter a department name.", "error")
            return redirect(url_for("admin_grant_create"))

        department = Department.query.filter(
            db.func.lower(Department.department_name) == department_name.lower()
        ).first()

        if not department:
            # Auto-create the department if it doesn't exist
            department = Department(
                department_name=department_name,
                department_description="(Created by Admin)"
            )
            db.session.add(department)
            db.session.commit()

        department_id = department.department_id

        # -----------------------------
        # 2) Validation rules
        # -----------------------------
        if action == "confirm":
            # require important fields
            if not (description and eligibiliity and open_date and close_date and max_budget and project_duration_limit):
                flash("Please fill in all required fields before confirming.", "error")
                return redirect(url_for("admin_grant_create"))

            if close_date < open_date:
                flash("Closing date must be after opening date.", "error")
                return redirect(url_for("admin_grant_create"))

        # convert numbers safely
        try:
            max_budget_int = int(max_budget) if max_budget else 0
            duration_int = int(project_duration_limit) if project_duration_limit else 0
        except ValueError:
            flash("Max Budget and Project Duration Limit must be numbers.", "error")
            return redirect(url_for("admin_grant_create"))

        scheme_status = "DRAFT" if action == "draft" else "OPEN"

        # -----------------------------
        # 3) Create scheme
        # -----------------------------
        scheme = GrantScheme(
            admin_id=admin.admin_id,
            department_id=department_id,
            description=description or "(Draft) - not final",
            eligibiliity=eligibiliity or "(Draft)",
            open_date=open_date or datetime.today().date(),
            close_date=close_date or datetime.today().date(),
            max_budget=max_budget_int,
            project_duration_limit=duration_int,
            required_documents=required_documents or "(Draft)",
            reporting_requirements=reporting_requirements or "(Draft)",
            scheme_status=scheme_status
        )

        db.session.add(scheme)
        db.session.commit()

        flash("Grant scheme saved!" if action == "draft" else "Grant scheme confirmed and opened!", "success")
        return redirect(url_for("admin_grants", status="ALL"))

    return render_template(
        "admin_grant_scheme_create.html",
        departments=departments,
        prof=prof
    )

@app.route("/admin/grants/<scheme_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_grant_view(scheme_id):
    scheme = GrantScheme.query.get_or_404(scheme_id)
    departments = Department.query.order_by(Department.department_name.asc()).all()

    st = (scheme.scheme_status or "").upper()

    if request.method == "POST":
        action = (request.form.get("action") or "").lower()

        # CLOSED: admin can ONLY view (block all modifications)
        if st == "CLOSED":
            flash("This scheme is CLOSED. You can only view it.", "error")
            return redirect(url_for("admin_grant_view", scheme_id=scheme_id))

        # OPEN: view/edit/delete (+ close allowed)
        if st == "OPEN":
            if action == "delete":
                db.session.delete(scheme)
                db.session.commit()
                flash("Scheme deleted.", "success")
                return redirect(url_for("admin_grants"))

            if action == "close":
                scheme.scheme_status = "CLOSED"
                db.session.commit()
                flash("Scheme closed.", "success")
                return redirect(url_for("admin_grants"))

            if action != "save":
                flash("Invalid action for an OPEN scheme.", "error")
                return redirect(url_for("admin_grant_view", scheme_id=scheme_id))

        # DRAFT: edit / confirm(open) / delete
        if st == "DRAFT":
            if action == "delete":
                db.session.delete(scheme)
                db.session.commit()
                flash("Draft scheme deleted.", "success")
                return redirect(url_for("admin_grants"))

            if action not in ("save", "open"):
                flash("Invalid action for a DRAFT scheme.", "error")
                return redirect(url_for("admin_grant_view", scheme_id=scheme_id))

        # ---- shared: update fields (OPEN or DRAFT, for save/open) ----
        dept_id = request.form.get("department_id")
        if dept_id:
            scheme.department_id = dept_id

        scheme.description = (request.form.get("description") or "").strip()
        scheme.eligibiliity = (request.form.get("eligibiliity") or "").strip()
        scheme.required_documents = (request.form.get("required_documents") or "").strip()
        scheme.reporting_requirements = (request.form.get("reporting_requirements") or "").strip()

        open_date = parse_date_yyyy_mm_dd(request.form.get("open_date"))
        close_date = parse_date_yyyy_mm_dd(request.form.get("close_date"))
        if open_date:
            scheme.open_date = open_date
        if close_date:
            scheme.close_date = close_date

        try:
            scheme.max_budget = int(request.form.get("max_budget") or scheme.max_budget)
            scheme.project_duration_limit = int(request.form.get("project_duration_limit") or scheme.project_duration_limit)
        except ValueError:
            flash("Max Budget and Project Duration Limit must be numbers.", "error")
            return redirect(url_for("admin_grant_view", scheme_id=scheme_id))

        # date validation
        if scheme.close_date and scheme.open_date and scheme.close_date < scheme.open_date:
            flash("Closing date must be after opening date.", "error")
            return redirect(url_for("admin_grant_view", scheme_id=scheme_id))

        # DRAFT confirm -> OPEN
        if st == "DRAFT" and action == "open":
            scheme.scheme_status = "OPEN"

        db.session.commit()
        flash("Scheme updated.", "success")
        return redirect(url_for("admin_grant_view", scheme_id=scheme_id))

    return render_template(
        "admin_grant_scheme_view.html",
        scheme=scheme,
        departments=departments
    )

#--------------------
#Funding Allocation
#--------------------
from sqlalchemy import or_

@app.route("/admin/funding")
@login_required
@admin_required
def admin_funding_list():
    q = (request.args.get("q") or "").strip()
    dept_id = (request.args.get("dept") or "").strip()   # department_id
    prof = get_profile(current_user.id)

    # dropdown options
    departments = Department.query.order_by(Department.department_name.asc()).all()

    # Base: only APPROVED proposals
    query = (
        db.session.query(Proposal, Department)
        .join(FinalDecision, FinalDecision.proposal_id == Proposal.proposal_id)
        .filter(db.func.upper(FinalDecision.decision) == "APPROVED")
        .join(GrantScheme, GrantScheme.scheme_id == Proposal.scheme_id)
        .join(Department, Department.department_id == GrantScheme.department_id)

        # Join funding tables (so we can exclude confirmed)
        .outerjoin(Project, Project.proposal_id == Proposal.proposal_id)
        .outerjoin(FundingAllocation, FundingAllocation.project_id == Project.project_id)

        # Show only proposals that are NOT confirmed funded yet
        # - no allocation yet OR allocation is not CONFIRMED
        .filter(
            or_(
                FundingAllocation.allocation_id.is_(None),
                db.func.upper(FundingAllocation.allocation_status) != "CONFIRMED"
            )
        )

        # If you set proposal_status="FUNDED" on confirm, exclude that too
        .filter(db.func.upper(db.func.coalesce(Proposal.proposal_status, "")) != "FUNDED")
    )

    # department filter
    if dept_id and dept_id != "ALL":
        query = query.filter(Department.department_id == dept_id)

    # search filter
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Proposal.project_title.ilike(like)) |
            (Department.department_name.ilike(like))
        )

    rows = query.order_by(Proposal.submission_date.desc()).all()

    return render_template(
        "admin_funding_allocation.html",
        rows=rows,
        q=q,
        dept=dept_id or "ALL",
        departments=departments,
        prof=prof
    )

@app.route("/admin/funding/<proposal_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_funding_allocate(proposal_id):
    prof = get_profile(current_user.id)
    admin = get_admin_by_user(current_user.id)
    if not admin:
        flash("Admin record not found for this user.", "error")
        return redirect(url_for("admin_dashboard"))

    proposal = Proposal.query.get_or_404(proposal_id)
    scheme = GrantScheme.query.get(proposal.scheme_id)
    department = Department.query.get(scheme.department_id) if scheme else None

    # Check if already allocated (Project exists)
    project = Project.query.filter_by(proposal_id=proposal.proposal_id).first()
    existing_allocation = None
    if project:
        existing_allocation = FundingAllocation.query.filter_by(project_id=project.project_id).first()

    if request.method == "POST":
        action = (request.form.get("action") or "draft").lower()  # draft / confirm

        # read amounts
        total_amount = request.form.get("total_amount") or "0"
        equipment_amount = request.form.get("equipment_amount") or "0"
        materials_amount = request.form.get("materials_amount") or "0"
        travel_amount = request.form.get("travel_amount") or "0"
        other_amount = request.form.get("other_amount") or "0"

        start_date = parse_date_yyyy_mm_dd(request.form.get("start_date"))
        end_date = parse_date_yyyy_mm_dd(request.form.get("end_date"))

        try:
            total_amount = int(total_amount)
            equipment_amount = int(equipment_amount)
            materials_amount = int(materials_amount)
            travel_amount = int(travel_amount)
            other_amount = int(other_amount)
        except ValueError:
            flash("All amounts must be numbers.", "error")
            return redirect(url_for("admin_funding_allocate", proposal_id=proposal_id))

        if any(x < 0 for x in [total_amount, equipment_amount, materials_amount, travel_amount, other_amount]):
            flash("Amounts cannot be negative.", "error")
            return redirect(url_for("admin_funding_allocate", proposal_id=proposal_id))

        # simple consistency check
        parts_sum = equipment_amount + materials_amount + travel_amount + other_amount
        if total_amount != parts_sum:
            flash("Total Budget must equal Equipment + Materials + Travel + Other.", "error")
            return redirect(url_for("admin_funding_allocate", proposal_id=proposal_id))

        if action == "confirm":
            proposal.proposal_status = "FUNDED"
            # validate dates
            if not start_date or not end_date:
                flash("Please fill in Start Date and End Date before confirming.", "error")
                return redirect(url_for("admin_funding_allocate", proposal_id=proposal_id))
            if end_date < start_date:
                flash("End Date must be after Start Date.", "error")
                return redirect(url_for("admin_funding_allocate", proposal_id=proposal_id))

        # ensure Project exists (one per proposal)
        if not project:
            project = Project(
                proposal_id=proposal.proposal_id,
                researcher_id=proposal.researcher_id,
                scheme_id=proposal.scheme_id,
                start_date=start_date or date.today(),
                end_date=end_date or date.today(),
                project_status="DRAFT" if action == "draft" else "ONGOING",
            )
            db.session.add(project)
            db.session.flush()  # get project_id without committing yet
        else:
            # update project dates/status
            if start_date:
                project.start_date = start_date
            if end_date:
                project.end_date = end_date
            project.project_status = "DRAFT" if action == "draft" else "ONGOING"

        # upsert FundingAllocation
        if not existing_allocation:
            existing_allocation = FundingAllocation(
                admin_id=admin.admin_id,
                project_id=project.project_id,
                total_amount=total_amount,
                equipment_amount=equipment_amount,
                materials_amount=materials_amount,
                travel_amount=travel_amount,
                other_amount=other_amount,
                allocation_status="DRAFT" if action == "draft" else "CONFIRMED",
            )
            db.session.add(existing_allocation)
        else:
            existing_allocation.admin_id = admin.admin_id
            existing_allocation.total_amount = total_amount
            existing_allocation.equipment_amount = equipment_amount
            existing_allocation.materials_amount = materials_amount
            existing_allocation.travel_amount = travel_amount
            existing_allocation.other_amount = other_amount
            existing_allocation.allocation_status = "DRAFT" if action == "draft" else "CONFIRMED"

        # update proposal status if confirmed
        if action == "confirm":
            proposal.proposal_status = "FUNDED"

        db.session.commit()
        flash("Funding saved as draft." if action == "draft" else "Funding confirmed!", "success")
        return redirect(url_for("admin_funding_list"))

    return render_template(
        "admin_funding_allocation_form.html",
        proposal=proposal,
        scheme=scheme,
        department=department,
        project=project,
        allocation=existing_allocation,
        prof=prof
    )

@app.route("/admin/proposals/<proposal_id>")
@login_required
@admin_required
def admin_view_proposal(proposal_id):
    proposal = Proposal.query.get_or_404(proposal_id)

    researcher = Researcher.query.get(proposal.researcher_id)
    scheme = GrantScheme.query.get(proposal.scheme_id)
    dept = Department.query.get(scheme.department_id) if scheme else None

    prof = get_profile(current_user.id)

    return render_template(
        "admin_view_proposal.html",
        proposal=proposal,
        researcher=researcher,
        scheme=scheme,
        dept=dept,
        prof=prof
    )

#-------------------------
#Final Approval Decision
#-------------------------
@app.route("/admin/final-approval")
@login_required
@admin_required
def admin_final_approval_list():
    q = (request.args.get("q") or "").strip()
    dept_id = (request.args.get("dept") or "ALL").strip()
    prof = get_profile(current_user.id)

    departments = Department.query.order_by(Department.department_name.asc()).all()

    # proposals that have NO final decision yet
    query = (
        db.session.query(Proposal, Department)
        .join(GrantScheme, GrantScheme.scheme_id == Proposal.scheme_id)
        .join(Department, Department.department_id == GrantScheme.department_id)
        .outerjoin(FinalDecision, FinalDecision.proposal_id == Proposal.proposal_id)
        .filter(FinalDecision.proposal_id.is_(None))
    )

    # optional: require HOD endorsement exists (so it's truly ready for final approval)
    query = query.join(HODEndorsement, HODEndorsement.proposal_id == Proposal.proposal_id)

    if dept_id != "ALL":
        query = query.filter(Department.department_id == dept_id)

    if q:
        like = f"%{q}%"
        query = query.filter(
            (Proposal.project_title.ilike(like)) |
            (Department.department_name.ilike(like))
        )

    rows = query.order_by(Proposal.submission_date.desc()).all()

    return render_template(
        "admin_final_approval_list.html",
        rows=rows,
        q=q,
        dept=dept_id,
        departments=departments,
        prof=prof
    )

@app.route("/admin/final-approval/<proposal_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_final_approval_detail(proposal_id):
    prof = get_profile(current_user.id)
    admin = get_admin_by_user(current_user.id)
    if not admin:
        flash("Admin record not found.", "error")
        return redirect(url_for("admin_dashboard"))

    proposal = Proposal.query.get_or_404(proposal_id)
    scheme = GrantScheme.query.get(proposal.scheme_id)
    dept = Department.query.get(scheme.department_id) if scheme else None

    # reviewer + hod status
    reviewer_status = compute_reviewer_recommendation(proposal.proposal_id)

    hod_endorse = HODEndorsement.query.filter_by(proposal_id=proposal.proposal_id).first()
    hod_status = "Pending"
    if hod_endorse:
        hod_status = "Endorsed" if (hod_endorse.decision or "").upper() == "ENDORSE" else "Not Endorsed"

    # if already decided, show it (and optionally block changes)
    existing_final = FinalDecision.query.filter_by(proposal_id=proposal.proposal_id).first()

    if request.method == "POST":
        action = (request.form.get("action") or "").lower()
        if action not in ("approve", "reject"):
            flash("Invalid action.", "error")
            return redirect(url_for("admin_final_approval_detail", proposal_id=proposal_id))

        decision = "APPROVED" if action == "approve" else "REJECTED"
        proposal.proposal_status = decision 

        if not existing_final:
            existing_final = FinalDecision(
                proposal_id=proposal.proposal_id,
                admin_id=admin.admin_id,
                decision=decision
            )
            db.session.add(existing_final)
        else:
            existing_final.admin_id = admin.admin_id
            existing_final.decision = decision
            existing_final.decision_date = datetime.now(timezone.utc)

        db.session.commit()
        flash(f"Final decision recorded: {decision}", "success")
        return redirect(url_for("admin_final_approval_list"))

    return render_template(
        "admin_final_approval_detail.html",
        proposal=proposal,
        scheme=scheme,
        dept=dept,
        reviewer_status=reviewer_status,
        hod_status=hod_status,
        final=existing_final,
        prof=prof
    )

#-------------------
# Assign Reviewers
#-------------------
def proposal_expertise_needed(dept_name: str) -> list[str]:
    """
    Simple mapping (no DB changes).
    Adjust to whatever categories you want.
    """
    mapping = {
        "Computer Science": ["AI", "Data Science", "Cybersecurity"],
        "Engineering": ["IoT", "Mechanical", "Civil"],
        "Business": ["Finance", "Marketing", "Analytics"],
        "Management": ["Project Management", "Operations", "Strategy"],
        "Multimedia": ["UI/UX", "AR/VR", "Game Design"],
    }
    return mapping.get(dept_name or "", ["General"])

def reviewer_expertise_tags(user: "User") -> list[str]:
    prof = UserProfile.query.filter_by(user_id=user.id).first()
    raw = (prof.expertise_tags or "").strip() if prof else ""
    if not raw:
        return ["General"]
    return [t.strip() for t in raw.split(",") if t.strip()]

@app.route("/admin/assign-reviewers")
@login_required
@admin_required
def admin_assign_reviewers():
    q = (request.args.get("q") or "").strip()
    dept_id = (request.args.get("dept") or "ALL").strip()
    prof = get_profile(current_user.id)

    departments = Department.query.order_by(Department.department_name.asc()).all()

    # Proposals that have NO reviewer assignments yet
    query = (
        db.session.query(Proposal, Department)
        .join(GrantScheme, GrantScheme.scheme_id == Proposal.scheme_id)
        .join(Department, Department.department_id == GrantScheme.department_id)
        .outerjoin(ReviewersAssignment, ReviewersAssignment.proposal_id == Proposal.proposal_id)
        .filter(ReviewersAssignment.proposal_id.is_(None))
    )

    if dept_id != "ALL":
        query = query.filter(Department.department_id == dept_id)

    if q:
        like = f"%{q}%"
        query = query.filter(
            (Proposal.project_title.ilike(like)) |
            (Department.department_name.ilike(like))
        )

    rows = query.order_by(Proposal.submission_date.desc()).all()

    return render_template(
        "admin_assign_reviewers.html",
        rows=rows,
        q=q,
        dept=dept_id,
        departments=departments,
        prof=prof
    )

@app.route("/admin/assign-reviewers/<proposal_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_assign_reviewer_detail(proposal_id):
    prof = get_profile(current_user.id)
    proposal = Proposal.query.get_or_404(proposal_id)

    scheme = GrantScheme.query.get(proposal.scheme_id)
    dept = Department.query.get(scheme.department_id) if scheme else None

    # Expertise needed label
    needed = proposal_expertise_needed(dept.department_name if dept else "")
    needed_str = ", ".join(needed)

    # Existing assignments for this proposal
    existing = ReviewersAssignment.query.filter_by(proposal_id=proposal.proposal_id).all()
    assigned_ids = {a.reviewer_id for a in existing}

    # Reviewer list (User + Reviewer)
    rq = (request.args.get("q") or "").strip()
    expertise_filter = (request.args.get("expertise") or "ALL").strip()

    reviewer_rows = (
        db.session.query(Reviewer, User)
        .join(User, User.id == Reviewer.user_id)
        .all()
    )

    # Build display list with expertise tags
    display = []
    all_tags = set()
    for rv, user in reviewer_rows:
        tags = reviewer_expertise_tags(user)
        for t in tags:
            all_tags.add(t)
        display.append({
            "reviewer": rv,
            "user": user,
            "tags": tags,
            "checked": (rv.reviewer_id in assigned_ids),
        })

    # Apply search
    if rq:
        rq_low = rq.lower()
        display = [
            x for x in display
            if rq_low in (x["user"].full_name or "").lower()
               or rq_low in (x["user"].email or "").lower()
        ]

    # Apply expertise filter
    if expertise_filter != "ALL":
        display = [x for x in display if expertise_filter in x["tags"]]

    # Sort: checked first, then name
    display.sort(key=lambda x: (0 if x["checked"] else 1, (x["user"].full_name or "").lower()))

    tags_sorted = ["ALL"] + sorted(all_tags)

    if request.method == "POST":
        selected = request.form.getlist("reviewer_id")

        # simple rules: choose 1-2 reviewers
        if len(selected) < 1:
            flash("Please select at least 1 reviewer.", "error")
            return redirect(url_for("admin_assign_reviewer_detail", proposal_id=proposal_id))
        if len(selected) > 2:
            flash("Please select up to 2 reviewers only.", "error")
            return redirect(url_for("admin_assign_reviewer_detail", proposal_id=proposal_id))

        # Remove old assignments (so re-assigning is easy)
        ReviewersAssignment.query.filter_by(proposal_id=proposal.proposal_id).delete()

        # Create new assignments
        for rid in selected:
            db.session.add(ReviewersAssignment(
                assignment_id=str(uuid.uuid4()),
                proposal_id=proposal.proposal_id,
                reviewer_id=rid,
                assignment_status="ASSIGNED"
            ))

        proposal.proposal_status = "PENDING_REVIEW"

        db.session.commit()
        flash("Reviewers assigned successfully.", "success")
        return redirect(url_for("admin_assign_reviewers"))

    return render_template(
        "admin_assign_reviewer_detail.html",
        proposal=proposal,
        dept=dept,
        needed_str=needed_str,
        reviewers=display,
        tags=tags_sorted,
        q=rq,
        expertise=expertise_filter,
        prof=prof
    )

#-----------------
# Proposal List
#-----------------
from sqlalchemy import func

@app.route("/admin/proposal-list")
@login_required
@admin_required
def admin_proposal_list():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "ALL").strip()  # KEEP as normal string (not .upper())

    query = Proposal.query

    if q:
        like = f"%{q}%"
        query = query.filter(Proposal.project_title.ilike(like))

    proposals = query.order_by(Proposal.proposal_id.desc()).all()

    # compute display status for each proposal
    for p in proposals:
        p.display_status = compute_proposal_display_status(p)

    # filter by computed display_status (this matches what the user sees)
    if status != "ALL":
        proposals = [p for p in proposals if (p.display_status == status)]

    return render_template(
        "admin_proposal_list.html",
        proposals=proposals,
        q=q,
        status=status,
        status_options=DISPLAY_STATUS_OPTIONS
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
