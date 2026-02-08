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
from sqlalchemy import exists, and_, or_, func, text
import uuid
import os

DISPLAY_STATUS_OPTIONS = [
    "Pending Assignment",
    "Pending Review",
    "Pending Endorsement",
    "Pending Approval",
    "Pending Funding",
    "Rejected",
    "Funded",
]

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'A&WGirlies'

app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB limit
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "docx"}

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
    expertise_needed = db.Column(db.String(500), nullable=True)
    submission_date = db.Column(db.DateTime, nullable=False)
    proposal_status = db.Column(db.String(15), nullable=False)

class ProposalAttachment(db.Model):
    attachment_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proposal_id = db.Column(
        db.String(36),
        db.ForeignKey('proposal.proposal_id'),
        nullable=False
    )
    stored_filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

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

class ActivityLog(db.Model):
    __tablename__ = "activity_log"
    activity_id = db.Column(db.String, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    actor_user_id = db.Column(db.String, nullable=True)     
    proposal_id = db.Column(db.String, nullable=True)       
    action = db.Column(db.String, nullable=False)           
    message = db.Column(db.String, nullable=False)          

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

def is_reviewer_user(user: User) -> bool:
    prof = get_profile(user.id)
    if not prof or prof.account_status != "ACTIVE" or prof.role != "REVIEWER":
        return False
    return Reviewer.query.filter_by(user_id=user.id).first() is not None

def reviewer_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not is_reviewer_user(current_user):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def get_reviewer_by_user(user_id: str):
    return Reviewer.query.filter_by(user_id=user_id).first()
def log_activity(message, action="INFO", proposal_id=None, actor_user_id=None, scheme_id=None, commit=False, **kwargs):
    db.session.add(ActivityLog(
        activity_id=str(uuid.uuid4()),
        action=action,
        message=message,
        proposal_id=proposal_id,
        actor_user_id=actor_user_id
    ))
    if commit:
        db.session.commit()

def create_notification(user_id: str, message: str, notif_type: str = "INFO", commit=False):
    """Helper function to create a notification for a user."""
    notification = Notification(
        user_id=user_id,
        message=message,
        notif_type=notif_type,
        created_at=datetime.now(timezone.utc),
        is_read=False
    )
    db.session.add(notification)
    if commit:
        db.session.commit()
    return notification

# ===========================
# Notification Helper Functions
# ===========================

def get_all_admin_user_ids():
    admins = Admin.query.all()
    return [a.user_id for a in admins if a.user_id]

def get_researcher_user_id_from_proposal(proposal):
    r = Researcher.query.get(proposal.researcher_id)
    return r.user_id if r else None

def get_reviewer_user_id(reviewer_id):
    rv = Reviewer.query.filter_by(reviewer_id=reviewer_id).first()
    return rv.user_id if rv else None

def get_hod_user_id_for_proposal(proposal):
    scheme = GrantScheme.query.get(proposal.scheme_id)
    if not scheme:
        return None
    
    dept = Department.query.get(scheme.department_id)
    if not dept or not dept.hod_id:
        return None
    
    hod = HOD.query.get(dept.hod_id)
    return hod.user_id if hod else None

from flask import abort

def get_or_404(model, pk):
    obj = db.session.get(model, pk)
    if not obj:
        abort(404)
    return obj

def ensure_user_profile_schema():
    # Lightweight migration for legacy SQLite DBs missing newer columns.
    with db.engine.connect() as conn:
        cols = conn.execute(text("PRAGMA table_info(user_profile)")).fetchall()
        if not cols:
            return
        col_names = {row[1] for row in cols}
        if "expertise_tags" not in col_names:
            conn.execute(text("ALTER TABLE user_profile ADD COLUMN expertise_tags VARCHAR(255)"))

@app.context_processor
def inject_profile():
    if current_user.is_authenticated:
        return {"prof": get_profile(current_user.id)}
    return {"prof": None}

@app.context_processor
def inject_unread_notifications():
    if current_user.is_authenticated:
        unread_count = (Notification.query
            .filter_by(user_id=current_user.id, is_read=False)
            .count())
        return {"unread_notifications": unread_count}
    return {"unread_notifications": 0}

from typing import Union

def compute_proposal_display_status(p_or_id: Union["Proposal", str]) -> str:
    # Accept either Proposal object or proposal_id string
    if isinstance(p_or_id, str):
        p = db.session.get(Proposal, p_or_id)
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
            # If not funded yet, it's pending funding
            project = Project.query.filter_by(proposal_id=pid).first()
            if project:
                alloc = FundingAllocation.query.filter_by(project_id=project.project_id).first()
                if alloc and (alloc.allocation_status or "").upper() == "CONFIRMED":
                    return "Funded"
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    error_message = None

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            prof = get_profile(user.id)

            if not prof:
                error_message = "Profile not found. Please contact admin."
            elif prof.account_status != "ACTIVE":
                error_message = "Your account is not active yet. Please wait for admin approval."
            else:
                login_user(user)
                # Route based on role
                if prof.role == "ADMIN":
                    return redirect(url_for("admin_users"))
                  
                elif prof.role == "RESEARCHER":
                    return redirect(url_for("researcher_dashboard"))
                return redirect(url_for('dashboard'))

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

    # HOD -> go to HOD dashboard
    if prof.role == "HOD":
        return redirect(url_for("hod_dashboard"))
    
    # Reviewer -> go to reviewer dashboard
    if prof.role == "REVIEWER":
        return redirect(url_for("reviewer_dashboard"))

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

@app.route("/notifications")
@login_required
def notifications():
    prof = get_profile(current_user.id)
    if not prof:
        flash("Profile not found. Please contact admin.", "error")
        return redirect(url_for("dashboard"))

    notifications_list = (Notification.query
        .filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all())

    return render_template(
        "notifications.html",
        prof=prof,
        notifications=notifications_list
    )

@app.route("/notifications/<notif_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notif_id):
    n = Notification.query.filter_by(
        notification_id=notif_id,
        user_id=current_user.id
    ).first_or_404()
    n.is_read = True
    db.session.commit()
    return redirect(url_for("notifications"))


@app.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({"is_read": True})
    db.session.commit()
    return redirect(url_for("notifications"))

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

        # department: only for researcher/reviewer/hod
        if prof.role in ("RESEARCHER", "REVIEWER", "HOD"):
            prof.department_name = (request.form.get("department_name") or "").strip()
        else:
            prof.department_name = None

        import time
        # profile picture upload
        file = request.files.get("profile_picture")
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Invalid file type. Please upload PNG/JPG/JPEG/GIF/PDF/DOCX only.", "error")
                return redirect(url_for("edit_profile"))

            ext = file.filename.rsplit(".", 1)[1].lower()
            filename = secure_filename(f"{current_user.id}.{ext}")  # stable name per user
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)

            old = prof.profile_picture
            if old:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], old)
                if os.path.exists(old_path):
                    os.remove(old_path)

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
        
        # Create notification for profile update
        create_notification(
            user_id=current_user.id,
            message="You've successfully updated your profile.",
            notif_type="PROFILE",
            commit=True
        )
        
        flash("Profile updated successfully!", "success")
        return redirect(url_for("view_profile"))

    return render_template(
        "edit_profile.html",
        user=current_user,
        prof=prof,
        departments=DEPARTMENTS
    )

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
# RESEARCHER ROUTES
#---------------------------------------------------------------------------------------------------------

@app.route("/researcher/dashboard")
@login_required
def researcher_dashboard():
    prof = get_profile(current_user.id)
    if not prof or prof.role != "RESEARCHER":
        flash("Access denied. Researcher role required.", "error")
        return redirect(url_for("dashboard"))
    
    researcher = get_researcher(current_user.id)
    if not researcher:
        flash("Researcher profile not found.", "error")
        return redirect(url_for("dashboard"))

    proposals_q = Proposal.query.filter_by(researcher_id=researcher.researcher_id)

    total_proposals = proposals_q.count()
    under_review = proposals_q.filter(
        db.func.lower(Proposal.proposal_status) == "under review"
    ).count()
    revision_required = proposals_q.filter(
        db.func.lower(Proposal.proposal_status).in_([
            "return for revision",
            "revision required",
        ])
    ).count()

    active_projects = Project.query.filter_by(researcher_id=researcher.researcher_id).filter(
        db.func.lower(Project.project_status).in_([
            "in progress",
            "in-progress",
            "active",
            "ongoing",
        ])
    ).count()

    recent_activity = []
    recent = proposals_q.order_by(Proposal.submission_date.desc()).limit(5).all()
    for proposal in recent:
        status = (proposal.proposal_status or "").strip().lower()
        title = proposal.project_title or "Proposal"

        if "pending" in status:
            message = f"{title} submitted"
        elif "under review" in status:
            message = f"{title} under review"
        elif "revision" in status:
            message = f"Revision requested for {title}"
        elif "approved" in status:
            message = f"{title} approved"
        elif "rejected" in status:
            message = f"{title} rejected"
        else:
            message = f"{title} status: {proposal.proposal_status}"

        recent_activity.append(message)

    return render_template(
        "researcher_dashboard.html",
        user=current_user,
        prof=prof,
        researcher=researcher,
        total_proposals=total_proposals,
        under_review=under_review,
        revision_required=revision_required,
        active_projects=active_projects,
        recent_activity=recent_activity,
    )

@app.route("/researcher/proposals")
@login_required
def researcher_proposals():
    prof = get_profile(current_user.id)
    if not prof or prof.role != "RESEARCHER":
        flash("Access denied. Researcher role required.", "error")
        return redirect(url_for("dashboard"))
    
    researcher = get_researcher(current_user.id)
    if not researcher:
        flash("Researcher profile not found.", "error")
        return redirect(url_for("dashboard"))
    
    proposals = Proposal.query.filter_by(researcher_id=researcher.researcher_id).all()
    return render_template("researcher_proposals.html", user=current_user, prof=prof, proposals=proposals)


@app.route("/researcher/proposals/create", methods=["GET", "POST"])
@login_required
def create_proposal():
    prof = get_profile(current_user.id)
    if not prof or prof.role != "RESEARCHER":
        flash("Access denied. Researcher role required.", "error")
        return redirect(url_for("dashboard"))

    researcher = get_researcher(current_user.id)
    if not researcher:
        flash("Researcher profile not found.", "error")
        return redirect(url_for("dashboard"))

    schemes = (
        db.session.query(GrantScheme)
        .order_by(GrantScheme.scheme_id.asc())
        .all()
    )

    if request.method == "POST":
        action = (request.form.get("action") or "submit").strip().lower()
        scheme_id = (request.form.get("scheme_id") or "").strip() or None
        title = (request.form.get("project_title") or "").strip()
        abstract = (request.form.get("abstract") or "").strip()
        methodology = (request.form.get("methodology") or "").strip()
        requested_budget = request.form.get("requested_budget") or 0
        expertise_needed = (request.form.get("expertise_needed") or "").strip()
        attachments = request.files.getlist("attachments")

        if not title or not abstract or not methodology:
            flash("Please fill in the required fields.", "error")
            return render_template(
                "create_proposal.html",
                user=current_user,
                prof=prof,
                schemes=schemes,
                proposal=None,
                form_action=url_for("create_proposal"),
            )

        scheme_id = (request.form.get("scheme_id") or "").strip()

        if not scheme_id:
            flash("Please select a grant scheme.", "error")
            return render_template(
                "create_proposal.html",
                user=current_user,
                prof=prof,
                schemes=schemes,
                proposal=None,
                form_action=url_for("create_proposal"),
            )

        scheme = GrantScheme.query.get(scheme_id)
        if not scheme:
            flash("Invalid grant scheme selected.", "error")
            return render_template(
                "create_proposal.html",
                user=current_user,
                prof=prof,
                schemes=schemes,
                proposal=None,
                form_action=url_for("create_proposal"),
            )

        proposal_status = "Draft" if action == "draft" else "Pending Review"

        new = Proposal(
            scheme_id=scheme_id,
            project_title=title,
            abstract=abstract,
            methodology=methodology,
            requested_budget=int(requested_budget),
            expertise_needed=expertise_needed,
            submission_date=datetime.now(timezone.utc),
            proposal_status=proposal_status,
            researcher_id=researcher.researcher_id
        )
        db.session.add(new)

        db.session.flush()

        for file in attachments:
            if not file or not file.filename:
                continue
            if not allowed_file(file.filename):
                flash("Invalid file type. Please upload PNG/JPG/JPEG/GIF/PDF/DOCX only.", "error")
                db.session.rollback()
                return render_template(
                    "create_proposal.html",
                    user=current_user,
                    prof=prof,
                    schemes=schemes,
                    proposal=None,
                    form_action=url_for("create_proposal"),
                )

            ext = file.filename.rsplit(".", 1)[1].lower()
            stored_name = secure_filename(f"{uuid.uuid4()}.{ext}")
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
            file.save(save_path)

            db.session.add(ProposalAttachment(
                proposal_id=new.proposal_id,
                stored_filename=stored_name,
                original_filename=file.filename,
            ))

        db.session.commit()
        if action == "draft":
            flash("Draft saved.", "success")
        else:
            db.session.add(new)
        db.session.flush()  # get new.proposal_id without committing yet

        # Notify HoD
        hod_user_id = get_hod_user_id_for_proposal(new)
        if hod_user_id:
            create_notification(
                user_id=hod_user_id,
                message=f"New proposal submitted: '{new.project_title}'. Please review/endorse when ready.",
                notif_type="PROPOSAL",
                commit=False
            )

        # Notify Admins
        for admin_user_id in get_all_admin_user_ids():
            create_notification(
                user_id=admin_user_id,
                message=f"New proposal submitted: '{new.project_title}'. It has entered the review pipeline.",
                notif_type="PROPOSAL",
                commit=False
        )

        # Notify Researcher (you already had this, but commit=False)
            create_notification(
                user_id=current_user.id,
                message=f"Your proposal '{title}' has been successfully submitted and is pending review.",
                notif_type="PROPOSAL",
                commit=False
            )

        db.session.commit()
            flash("Proposal submitted successfully.", "success")
        return redirect(url_for("researcher_proposals"))

    return render_template(
        "create_proposal.html",
        user=current_user,
        prof=prof,
        schemes=schemes,
        proposal=None,
        form_action=url_for("create_proposal"),
    )


@app.route("/researcher/proposals/<proposal_id>/edit", methods=["GET", "POST"])
@login_required
def edit_proposal(proposal_id):
    prof = get_profile(current_user.id)
    if not prof or prof.role != "RESEARCHER":
        flash("Access denied. Researcher role required.", "error")
        return redirect(url_for("dashboard"))

    researcher = get_researcher(current_user.id)
    if not researcher:
        flash("Researcher profile not found.", "error")
        return redirect(url_for("dashboard"))

    proposal = Proposal.query.get_or_404(proposal_id)
    if proposal.researcher_id != researcher.researcher_id:
        abort(403)

    editable_statuses = {
        "draft",
        "return for revision",
        "returned for revision",
        "revision required",
    }
    if (proposal.proposal_status or "").strip().lower() not in editable_statuses:
        flash("Only draft or revision-required proposals can be edited.", "error")
        return redirect(url_for("researcher_proposals"))

    schemes = GrantScheme.query.all()

    if request.method == "POST":
        action = (request.form.get("action") or "submit").strip().lower()
        scheme_id = (request.form.get("scheme_id") or "").strip() or None
        title = (request.form.get("project_title") or "").strip()
        abstract = (request.form.get("abstract") or "").strip()
        methodology = (request.form.get("methodology") or "").strip()
        requested_budget = request.form.get("requested_budget") or 0
        expertise_needed = (request.form.get("expertise_needed") or "").strip()
        attachments = request.files.getlist("attachments")

        if not title:
            flash("Please add a proposal title before saving.", "error")
            return render_template(
                "create_proposal.html",
                user=current_user,
                prof=prof,
                schemes=schemes,
                proposal=proposal,
                form_action=url_for("edit_proposal", proposal_id=proposal.proposal_id),
            )

        if action == "submit" and (not abstract or not methodology):
            flash("Please fill in the required fields.", "error")
            return render_template(
                "create_proposal.html",
                user=current_user,
                prof=prof,
                schemes=schemes,
                proposal=proposal,
                form_action=url_for("edit_proposal", proposal_id=proposal.proposal_id),
            )

        proposal.scheme_id = scheme_id
        proposal.project_title = title
        proposal.abstract = abstract
        proposal.methodology = methodology
        proposal.requested_budget = int(requested_budget)
        proposal.expertise_needed = expertise_needed

        if action == "submit":
            proposal.proposal_status = "Pending Review"
            proposal.submission_date = datetime.now(timezone.utc)

        for file in attachments:
            if not file or not file.filename:
                continue
            if not allowed_file(file.filename):
                flash("Invalid file type. Please upload PNG/JPG/JPEG/GIF/PDF/DOCX only.", "error")
                db.session.rollback()
                return render_template(
                    "create_proposal.html",
                    user=current_user,
                    prof=prof,
                    schemes=schemes,
                    proposal=proposal,
                    form_action=url_for("edit_proposal", proposal_id=proposal.proposal_id),
                )

            ext = file.filename.rsplit(".", 1)[1].lower()
            stored_name = secure_filename(f"{uuid.uuid4()}.{ext}")
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
            file.save(save_path)

            db.session.add(ProposalAttachment(
                proposal_id=proposal.proposal_id,
                stored_filename=stored_name,
                original_filename=file.filename,
            ))

        db.session.commit()
        if action == "draft":
            flash("Draft updated.", "success")
        else:
            flash("Proposal submitted successfully.", "success")
        return redirect(url_for("researcher_proposals"))

    return render_template(
        "create_proposal.html",
        user=current_user,
        prof=prof,
        schemes=schemes,
        proposal=proposal,
        form_action=url_for("edit_proposal", proposal_id=proposal.proposal_id),
    )


@app.route("/researcher/proposals/<proposal_id>")
@login_required
def view_proposal(proposal_id):
    prof = get_profile(current_user.id)
    if not prof or prof.role != "RESEARCHER":
        flash("Access denied.", "error")
        return redirect(url_for("dashboard"))

    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)

    if (proposal.proposal_status or "").strip().lower() == "draft":
        return redirect(url_for("edit_proposal", proposal_id=proposal.proposal_id))

    attachments = ProposalAttachment.query.filter_by(proposal_id=proposal.proposal_id).all()

    return render_template(
        "view_proposal.html",
        user=current_user,
        prof=prof,
        proposal=proposal,
        attachments=attachments,
    )


@app.route("/researcher/proposals/<proposal_id>/feedback")
@login_required
def view_proposal_feedback(proposal_id):
    prof = get_profile(current_user.id)
    if not prof or prof.role != "RESEARCHER":
        flash("Access denied.", "error")
        return redirect(url_for("dashboard"))

    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)

    reviews = (
        Review.query.filter_by(proposal_id=proposal_id)
        .order_by(Review.review_date.desc())
        .all()
    )
    latest_review = reviews[0] if reviews else None
    hod_feedback = (
        HODEndorsement.query.filter_by(proposal_id=proposal_id)
        .order_by(HODEndorsement.decision_date.desc())
        .first()
    )

    return render_template(
        "view_proposal_feedback.html",
        user=current_user,
        prof=prof,
        proposal=proposal,
        reviews=reviews,
        latest_review=latest_review,
        hod_feedback=hod_feedback,
    )

@app.route("/researcher/projects")
@login_required
def researcher_projects():
    prof = get_profile(current_user.id)
    if not prof or prof.role != "RESEARCHER":
        flash("Access denied. Researcher role required.", "error")
        return redirect(url_for("dashboard"))
    
    researcher = get_researcher(current_user.id)
    if not researcher:
        flash("Researcher profile not found.", "error")
        return redirect(url_for("dashboard"))
    
    projects = (
        db.session.query(Project, Proposal)
        .join(Proposal, Project.proposal_id == Proposal.proposal_id)
        .filter(Project.researcher_id == researcher.researcher_id)
        .all()
    )
    return render_template("researcher_projects.html", user=current_user, prof=prof, projects=projects)

#---------------------------------------------------------------------------------------------------------
# ADMIN ROUTES
#---------------------------------------------------------------------------------------------------------

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
    funded_proposals = 0

    for p in proposals:
        st = compute_proposal_display_status(p)

        if st == "Pending Assignment":
            pending_reviewer_assignment += 1
        elif st == "Pending Endorsement":
            awaiting_hod_decision += 1
        elif st == "Pending Approval":
            final_approval_needed += 1
        elif st == "Funded":
            funded_proposals += 1

    pending_funding_q = (
        db.session.query(Proposal.proposal_id)
        .join(FinalDecision, FinalDecision.proposal_id == Proposal.proposal_id)
        .filter(db.func.upper(FinalDecision.decision) == "APPROVED")
        .join(GrantScheme, GrantScheme.scheme_id == Proposal.scheme_id)
        .outerjoin(Project, Project.proposal_id == Proposal.proposal_id)
        .outerjoin(FundingAllocation, FundingAllocation.project_id == Project.project_id)
        .filter(
            or_(
                FundingAllocation.allocation_id.is_(None),
                db.func.upper(FundingAllocation.allocation_status) != "CONFIRMED"
            )
        )
        .filter(db.func.upper(db.func.coalesce(Proposal.proposal_status, "")) != "FUNDED")
    )

    awaiting_budget_allocation = pending_funding_q.count()

    # --- grant schemes ---
    active_grant_schemes = GrantScheme.query.filter_by(scheme_status="OPEN").count()

    # --- Recent Activity 
    recent_activity_rows = (
        ActivityLog.query
        .order_by(ActivityLog.created_at.desc())
        .limit(5)
        .all()
    )

    recent_activity = [a.message for a in recent_activity_rows]

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
        funded_proposals=funded_proposals,

        # recent activity list
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

    u = db.session.get(User, user_id)
    log_activity(
        f"User '{u.full_name}' approved and role set to {role}",
        action="APPROVE_USER",
        actor_user_id=current_user.id,
    )

    db.session.commit()
    return redirect(url_for("admin_users", status="PENDING"))

@app.route("/admin/users/<user_id>/reject", methods=["POST"])
@login_required
@admin_required
def admin_reject_user(user_id):
    # 1) Fetch user FIRST (so we still have name/email before deleting)
    user = User.query.get(user_id)
    user_name = user.full_name if user else "Unknown"
    user_email = user.email if user else "Unknown"

    # 2) Delete profile + user
    prof = get_profile(user_id)
    if prof:
        db.session.delete(prof)
    if user:
        db.session.delete(user)

    # 3) Log BEFORE commit (safe + included in same transaction)
    log_activity(
        f"User '{user_name}' rejected and removed ({user_email})",
        action="REJECT_USER",
        actor_user_id=current_user.id
    )

    # 4) Commit once
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
    u = db.session.get(User, user_id)

    log_activity(
        f"User '{u.full_name}' deactivated",
        action="DEACTIVATE_USER",
        actor_user_id=current_user.id,
    )

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
    u = db.session.get(User, user_id)

    log_activity(
        f"User '{u.full_name}' activated",
        action="ACTIVATE_USER",
        actor_user_id=current_user.id,
    )

    db.session.commit()
    return redirect(url_for("admin_users", status="DEACTIVATED"))

@app.route("/admin/users/<user_id>/remove", methods=["POST"])
@login_required
@admin_required
def admin_remove_user(user_id):
    # 1) Fetch user FIRST
    user = User.query.get(user_id)
    user_name = user.full_name if user else "Unknown"
    user_email = user.email if user else "Unknown"

    # 2) Delete profile + user
    prof = get_profile(user_id)
    if prof:
        db.session.delete(prof)
    if user:
        db.session.delete(user)

    # 3) Log BEFORE commit
    log_activity(
        f"User '{user_name}' removed ({user_email})",
        action="REMOVE_USER",
        actor_user_id=current_user.id
    )

    # 4) Commit once
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

    log_activity(
        f"Admin created user '{new_user.full_name}' ({new_user.email}) with role {role}",
        action="CREATE_USER",
        actor_user_id=current_user.id,
    )

    flash(f"User created successfully. Temporary password: {temp_password}", "success")
    return redirect(url_for("admin_users", status="ACTIVE"))

@app.route("/admin/users/<user_id>/profile")
@login_required
@admin_required
def admin_view_user_profile(user_id):
    user = User.query.get_or_404(user_id)

    # clicked user's profile
    target_prof = UserProfile.query.filter_by(user_id=user_id).first()

    # role tables (optional — only if exists)
    admin_row = Admin.query.filter_by(user_id=user_id).first()
    hod_row = HOD.query.filter_by(user_id=user_id).first()
    reviewer_row = Reviewer.query.filter_by(user_id=user_id).first()
    researcher_row = Researcher.query.filter_by(user_id=user_id).first()

    # admin's own profile (for topbar avatar)
    prof = get_profile(current_user.id)

    return render_template(
        "admin_view_user_profile.html",
        user=user,
        target_prof=target_prof,
        admin_row=admin_row,
        hod_row=hod_row,
        reviewer_row=reviewer_row,
        researcher_row=researcher_row,
        prof=prof
    )

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

    departments = Department.query.order_by(Department.department_name.asc()).all()

    if not admin:
        flash("Admin record not found for this user.", "error")
        return redirect(url_for("admin_dashboard"))

    # -----------------------------
    # GET: show form
    # -----------------------------
    if request.method == "GET":
        return render_template(
            "admin_grant_scheme_create.html",
            departments=departments,
            prof=prof
        )

    # -----------------------------
    # POST: read inputs
    # -----------------------------
    department_name = (request.form.get("department_name") or "").strip()
    description = (request.form.get("description") or "").strip()
    eligibiliity = (request.form.get("eligibiliity") or "").strip()
    required_documents = (request.form.get("required_documents") or "").strip()
    reporting_requirements = (request.form.get("reporting_requirements") or "").strip()

    open_date = parse_date_yyyy_mm_dd(request.form.get("open_date"))
    close_date = parse_date_yyyy_mm_dd(request.form.get("close_date"))

    max_budget_raw = (request.form.get("max_budget") or "").strip()
    project_duration_raw = (request.form.get("project_duration_limit") or "").strip()

    action = (request.form.get("action") or "draft").lower()  # draft / confirm

    # -----------------------------
    # 1) Department: required + auto-create if missing
    # -----------------------------
    if not department_name:
        flash("Please enter a department name.", "error")
        return redirect(url_for("admin_grant_create"))

    department = Department.query.filter(
        db.func.lower(Department.department_name) == department_name.lower()
    ).first()

    if not department:
        department = Department(
            department_name=department_name,
            department_description="(Created by Admin)"
        )
        db.session.add(department)
        db.session.commit()

    department_id = department.department_id

    # -----------------------------
    # 2) Validation rules (Draft + Confirm)
    # -----------------------------
    # Always validate date order if both are provided
    if open_date and close_date and close_date < open_date:
        flash("Closing date must be after opening date.", "error")
        return redirect(url_for("admin_grant_create"))

    # Only "confirm" requires all required fields
    if action == "confirm":
        if not (description and eligibiliity and open_date and close_date and max_budget_raw and project_duration_raw):
            flash("Please fill in all required fields before confirming.", "error")
            return redirect(url_for("admin_grant_create"))

    # -----------------------------
    # 3) Convert numeric fields safely (Draft + Confirm)
    # -----------------------------
    try:
        max_budget_int = int(max_budget_raw) if max_budget_raw else 0
        duration_int = int(project_duration_raw) if project_duration_raw else 0
    except ValueError:
        flash("Max Budget and Project Duration Limit must be numbers.", "error")
        return redirect(url_for("admin_grant_create"))

    # -----------------------------
    # 4) Set status
    # -----------------------------
    scheme_status = "DRAFT" if action == "draft" else "OPEN"

    # -----------------------------
    # 5) Create scheme (Draft + Confirm)
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

    # log after commit so scheme exists
    log_activity(
        f"Grant scheme created for '{department.department_name}': {scheme.description} ({scheme.scheme_status})",
        action="CREATE_GRANT_SCHEME",
        actor_user_id=current_user.id,
    )

    flash(
        "Grant scheme saved as draft!" if action == "draft" else "Grant scheme confirmed and opened!",
        "success"
    )
    return redirect(url_for("admin_grants", status="ALL"))

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

                log_activity(
                    f"Grant scheme deleted: {scheme.description}",
                    action="DELETE_GRANT_SCHEME",
                    actor_user_id=current_user.id,
                )

                db.session.delete(scheme)
                db.session.commit()

                flash("Scheme deleted.", "success")
                return redirect(url_for("admin_grants"))

            if action == "close":
                scheme.scheme_status = "CLOSED"

                log_activity(
                    f"Grant scheme closed: {scheme.description}",
                    action="CLOSE_GRANT_SCHEME",
                    actor_user_id=current_user.id,
                    scheme_id=scheme_id
                )

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

        log_activity(
            f"Grant scheme updated: {scheme.description} (status: {scheme.scheme_status})",
            action="UPDATE_GRANT_SCHEME",
            actor_user_id=current_user.id,
            scheme_id=scheme_id
        )

        db.session.commit()

        flash("Scheme updated.", "success")
        return redirect(url_for("admin_grant_view", scheme_id=scheme_id))

    return render_template(
        "admin_view_grant_scheme.html",
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
    tab = (request.args.get("tab") or "ALL").upper()   # ALL / NO_ALLOC / DRAFT

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

    if tab == "NO_ALLOC":
        query = query.filter(FundingAllocation.allocation_id.is_(None))

    elif tab == "DRAFT":
        query = query.filter(
            FundingAllocation.allocation_id.is_not(None),
            db.func.upper(FundingAllocation.allocation_status) == "DRAFT"
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
        tab=tab,
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

            researcher_id = get_researcher_user_id_from_proposal(proposal)
            create_notification(
                user_id=researcher_id,
                message=f"Funding allocated for '{proposal.project_title}'. Project is now ongoing.",
                notif_type="FUNDING",
                commit=False
            )

        if action == "draft":
            log_activity(
                f"Funding drafted for '{proposal.project_title}' (Total: {total_amount})",
                action="DRAFT_FUNDING",
                proposal_id=proposal.proposal_id,
                actor_user_id=current_user.id
            )
        else:
            log_activity(
                f"Funding confirmed for '{proposal.project_title}' (Total: {total_amount})",
                action="CONFIRM_FUNDING",
                proposal_id=proposal.proposal_id,
                actor_user_id=current_user.id
            )
            # Notify researcher about funding confirmation
            researcher = Researcher.query.get(proposal.researcher_id)
            if researcher:
                create_notification(
                    user_id=researcher.user_id,
                    message=f"Funding of ${total_amount:,} has been confirmed for your project '{proposal.project_title}'.",
                    notif_type="FUNDING"
                )

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

#----------------
# View Buttons
#----------------
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

@app.route("/admin/proposals/<proposal_id>/recommendation")
@login_required
@admin_required
def admin_view_recommendation(proposal_id):
    proposal = Proposal.query.get_or_404(proposal_id)

    # All reviews for this proposal (what reviewers submitted)
    reviews = (
        Review.query
        .filter_by(proposal_id=proposal_id)
        .order_by(Review.review_date.desc())
        .all()
    )

    # optional extra info for the header
    researcher = Researcher.query.get(proposal.researcher_id)
    scheme = GrantScheme.query.get(proposal.scheme_id)
    dept = Department.query.get(scheme.department_id) if scheme else None

    prof = get_profile(current_user.id)

    return render_template(
        "admin_view_recommendation.html",
        proposal=proposal,
        researcher=researcher,
        scheme=scheme,
        dept=dept,
        reviews=reviews,
        prof=prof
    )


@app.route("/admin/proposals/<proposal_id>/endorsement")
@login_required
@admin_required
def admin_view_endorsement(proposal_id):
    proposal = Proposal.query.get_or_404(proposal_id)

    endorsement = HODEndorsement.query.filter_by(proposal_id=proposal_id).first()

    researcher = Researcher.query.get(proposal.researcher_id)
    scheme = GrantScheme.query.get(proposal.scheme_id)
    dept = Department.query.get(scheme.department_id) if scheme else None

    prof = get_profile(current_user.id)

    return render_template(
        "admin_view_endorsement.html",
        proposal=proposal,
        researcher=researcher,
        scheme=scheme,
        dept=dept,
        endorsement=endorsement,
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

    # HOD endorsement exists
    query = query.join(HODEndorsement, HODEndorsement.proposal_id == Proposal.proposal_id)
    # Only endorsed by HoD
    query = query.filter(db.func.upper(HODEndorsement.decision) == "ENDORSE")

    if dept_id != "ALL":
        query = query.filter(Department.department_id == dept_id)

    if q:
        like = f"%{q}%"
        query = query.filter(
            (Proposal.project_title.ilike(like)) |
            (Department.department_name.ilike(like))
        )

    rows = query.order_by(Proposal.submission_date.desc()).all()
    # Only include proposals that reviewers recommended
    rows = [(p, d) for (p, d) in rows if compute_reviewer_recommendation(p.proposal_id) == "Recommended"]

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

    if reviewer_status != "Recommended" or hod_status != "Endorsed":
        flash("This proposal is not ready for final approval (must be Recommended + Endorsed).", "error")
        return redirect(url_for("admin_final_approval_list"))

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

        log_activity(
            f"Final decision {decision.title()} for '{proposal.project_title}'",
            action="FINAL_DECISION",
            proposal_id=proposal.proposal_id,
            actor_user_id=current_user.id
        )

        researcher_id = get_researcher_user_id_from_proposal(proposal)
        if researcher_id:
            create_notification(
            user_id=researcher_id,
            message=f"Final decision for '{proposal.project_title}': {decision.decision}",
            notif_type="FINAL",
            commit=False
        )

        db.session.commit()
        
        # Notify the researcher about the decision
        researcher = Researcher.query.get(proposal.researcher_id)
        if researcher:
            decision_text = "approved" if decision == "APPROVED" else "rejected"
            create_notification(
                user_id=researcher.user_id,
                message=f"Your proposal '{proposal.project_title}' has been {decision_text}.",
                notif_type="DECISION",
                commit=True
            )

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

        reviewer_prof = get_profile(user.id)   # <--- add this
        pic = reviewer_prof.profile_picture if reviewer_prof else None  # <--- add this

        display.append({
            "reviewer": rv,
            "user": user,
            "tags": tags,
            "checked": (rv.reviewer_id in assigned_ids),
            "profile_picture": pic,            # <--- add this
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

        for rid in selected:
            rv = Reviewer.query.filter_by(reviewer_id=rid).first()
            reviewer_user = User.query.get(rv.user_id) if rv else None

            if reviewer_user:
                log_activity(
                f"Proposal '{proposal.project_title}' assigned to {reviewer_user.full_name}",
                action="ASSIGN_REVIEWER",
                proposal_id=proposal.proposal_id,
                actor_user_id=current_user.id
            )

            create_notification(
                user_id=reviewer_user.id,
                message=f"You have been assigned to review proposal '{proposal.project_title}'.",
                notif_type="ASSIGNMENT",
                commit=False
            )

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

#---------------------------------------------------------------------------------------------------------
# HOD ROUTES
#---------------------------------------------------------------------------------------------------------

DEPARTMENTS = [
    "Engineering & Robotics",
    "Biology & Biotechnology",
    "Cybersecurity & Digital Forensics",
    "Information Technology",
    "Computer Science",
    "Social Sciences & Humanities",
    "Medicine & Health Sciences",
]

PROJECT_STATUS = [
    "PENDING",
    "IN PROGRESS",
    "CANCALLED",
]

@app.route("/HOD/dashboard")
@login_required
def hod_dashboard():
    return render_template("hod_dashboard.html")

@app.route("/HOD/department-overview", methods=["GET", "POST"])
@login_required
def hod_department_overview():
    prof = get_profile(current_user.id)
    if not prof or prof.role != "HOD":
        flash("Access denied. HOD role required.", "error")
        return redirect(url_for("dashboard"))

    department_name = (prof.department_name or "").strip()
    department = None
    if department_name:
        department = Department.query.filter(
            func.lower(Department.department_name) == department_name.lower()
        ).first()

    if request.method == "POST":
        new_description = (request.form.get("department_description") or "").strip()

        if not department_name:
            flash("Department is not set for this HOD.", "error")
            return redirect(url_for("hod_department_overview"))

        if not new_description:
            flash("Please enter a department description.", "error")
            return redirect(url_for("hod_department_overview"))

        if department:
            department.department_description = new_description
        else:
            hod_row = HOD.query.filter_by(user_id=current_user.id).first()
            department = Department(
                department_name=department_name,
                department_description=new_description,
                hod_id=hod_row.hod_id if hod_row else None
            )
            db.session.add(department)

        db.session.commit()
        flash("Department description updated.", "success")
        return redirect(url_for("hod_department_overview"))

    member_count = 0
    if department_name:
        member_count = UserProfile.query.filter(
            func.lower(UserProfile.department_name) == department_name.lower(),
            UserProfile.role.in_(["RESEARCHER", "REVIEWER", "HOD"])
        ).count()

    reviewer_rows = []
    researcher_rows = []
    if department_name:
        reviewer_rows = (db.session.query(User, UserProfile)
            .join(UserProfile, UserProfile.user_id == User.id)
            .filter(
                func.lower(UserProfile.department_name) == department_name.lower(),
                UserProfile.role == "REVIEWER"
            )
            .order_by(UserProfile.created_at.desc())
            .limit(3)
            .all())

        researcher_rows = (db.session.query(User, UserProfile)
            .join(UserProfile, UserProfile.user_id == User.id)
            .filter(
                func.lower(UserProfile.department_name) == department_name.lower(),
                UserProfile.role == "RESEARCHER"
            )
            .order_by(UserProfile.created_at.desc())
            .limit(3)
            .all())

    recent_reviewers = [
        {"full_name": u.full_name, "profile_picture": p.profile_picture}
        for u, p in reviewer_rows
    ]
    recent_researchers = [
        {"full_name": u.full_name, "profile_picture": p.profile_picture}
        for u, p in researcher_rows
    ]

    return render_template(
        "hod_department_overview.html",
        prof=prof,
        department_name=department_name or "Department",
        member_count=member_count,
        recent_reviewers=recent_reviewers,
        recent_researchers=recent_researchers,
        department_description=(department.department_description if department else "")
    )

@app.route("/HOD/active-projects")
@login_required
def hod_active_projects():
    prof = get_profile(current_user.id)
    if not prof or prof.role != "HOD":
        flash("Access denied. HOD role required.", "error")
        return redirect(url_for("dashboard"))

    q = (request.args.get("q") or "").strip()
    status_filter = (request.args.get("status") or "").strip().upper()
    department_name = (prof.department_name or "").strip()
    projects = []

    if department_name:
        query = (
            db.session.query(
                Project.project_id,
                Project.project_status,
                Project.start_date,
                Project.end_date,
                Proposal.project_title,
                User.full_name
            )
            .join(Proposal, Proposal.proposal_id == Project.proposal_id)
            .join(Researcher, Researcher.researcher_id == Project.researcher_id)
            .join(User, User.id == Researcher.user_id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .filter(
                func.lower(UserProfile.department_name) == department_name.lower(),
                UserProfile.role == "RESEARCHER"
            )
        )

        # Apply status filter
        if status_filter == "ONGOING":
            query = query.filter(func.upper(Project.project_status) == "IN PROGRESS")
        elif status_filter == "COMPLETED":
            query = query.filter(func.upper(Project.project_status) == "COMPLETED")
        elif status_filter == "ON-HOLD":
            query = query.filter(func.upper(Project.project_status) == "ON HOLD")
        else:
            # Default: show only IN PROGRESS projects
            query = query.filter(func.upper(Project.project_status) == "IN PROGRESS")

        # Apply search filter
        if q:
            query = query.filter(Proposal.project_title.ilike(f"%{q}%"))

        query = query.order_by(Project.start_date.desc())
        project_rows = query.all()

        for proj_id, proj_status, start_date, end_date, proj_title, user_name in project_rows:
            projects.append({
                "project_id": proj_id,
                "project_title": proj_title,
                "researcher_name": user_name,
                "status": proj_status,
                "start_date": start_date,
                "end_date": end_date
            })

    return render_template(
        "hod_active_projects.html",
        prof=prof,
        projects=projects,
        department_name=department_name or "Department",
        q=q,
        status_filter=status_filter
    )

@app.route("/HOD/review-proposals")
@login_required
def hod_review_proposals():
    prof = get_profile(current_user.id)
    if not prof or prof.role != "HOD":
        flash("Access denied.", "error")
        return redirect(url_for("dashboard"))

    schemes = GrantScheme.query.join(Department).filter(
        Department.department_name == prof.department_name
    ).all()

    scheme_ids = [s.scheme_id for s in schemes]

    proposals = Proposal.query.filter(
        Proposal.scheme_id.in_(scheme_ids)
    ).order_by(Proposal.submission_date.desc()).all()

    return render_template(
        "hod_review_proposals.html",
        prof=prof,
        proposals=proposals,
        department_name=prof.department_name
    )

@app.route("/HOD/endorse/<proposal_id>", methods=["POST"])
@login_required
def hod_endorse(proposal_id):
    prof = get_profile(current_user.id)
    if not prof or prof.role != "HOD":
        flash("Access denied.", "error")
        return redirect(url_for("dashboard"))

    proposal = Proposal.query.get_or_404(proposal_id)

    # Ensure proposal belongs to HoD department
    scheme = GrantScheme.query.get(proposal.scheme_id)
    dept = Department.query.get(scheme.department_id) if scheme else None
    if not dept or dept.department_name != prof.department_name:
        flash("Access denied. Not your department proposal.", "error")
        return redirect(url_for("hod_review_proposals"))

    decision = (request.form.get("decision") or "").strip().upper()  # ENDORSE / REJECT
    remarks = (request.form.get("remarks") or "").strip()

    if decision not in {"ENDORSE", "REJECT"}:
        flash("Invalid decision.", "error")
        return redirect(url_for("hod_review_proposals"))

    hod = HOD.query.filter_by(user_id=current_user.id).first()
    if not hod:
        flash("HOD record not found.", "error")
        return redirect(url_for("hod_dashboard"))

    # Upsert endorsement
    hod_endorsement = HODEndorsement.query.filter_by(proposal_id=proposal_id).first()
    if not hod_endorsement:
        hod_endorsement = HODEndorsement(
            endorsement_id=str(uuid.uuid4()),
            proposal_id=proposal_id,
            hod_id=hod.hod_id,
            decision=decision,
            remarks=remarks,
            endorsement_date=datetime.now(timezone.utc)
        )
        db.session.add(hod_endorsement)
    else:
        hod_endorsement.decision = decision
        hod_endorsement.remarks = remarks
        hod_endorsement.endorsement_date = datetime.now(timezone.utc)

    db.session.flush()

    # ===== Notifications =====
    researcher_user_id = get_researcher_user_id_from_proposal(proposal)

    if researcher_user_id:
        create_notification(
            user_id=researcher_user_id,
            message=f"HoD decision recorded for '{proposal.project_title}': {decision}.",
            notif_type="HOD",
            commit=False
        )

    for admin_user_id in get_all_admin_user_ids():
        create_notification(
            user_id=admin_user_id,
            message=f"HoD decision submitted for '{proposal.project_title}': {decision}.",
            notif_type="HOD",
            commit=False
        )

    db.session.commit()
    flash("HoD decision submitted.", "success")
    return redirect(url_for("hod_review_proposals"))

@app.route("/HOD/reviewers")
@login_required
def hod_reviewers():
    prof = get_profile(current_user.id)
    if not prof or prof.role != "HOD":
        flash("Access denied. HOD role required.", "error")
        return redirect(url_for("dashboard"))

    q = (request.args.get("q") or "").strip()
    filter_by = (request.args.get("filter") or "").strip().lower()
    department_name = (prof.department_name or "").strip()
    reviewers = []
    if department_name:
        review_counts = (
            db.session.query(
                Review.reviewer_id,
                func.count(Review.review_id).label("reviewed_count")
            )
            .group_by(Review.reviewer_id)
            .subquery()
        )

        query = (
            db.session.query(
                User,
                UserProfile,
                Reviewer,
                func.coalesce(review_counts.c.reviewed_count, 0).label("reviewed_count")
            )
            .join(UserProfile, UserProfile.user_id == User.id)
            .join(Reviewer, Reviewer.user_id == User.id)
            .outerjoin(review_counts, review_counts.c.reviewer_id == Reviewer.reviewer_id)
            .filter(
                func.lower(UserProfile.department_name) == department_name.lower(),
                UserProfile.role == "REVIEWER"
            )
        )

        if filter_by == "name" and q:
            query = query.filter(User.full_name.ilike(f"%{q}%"))
        elif filter_by == "email" and q:
            query = query.filter(User.email.ilike(f"%{q}%"))
        elif filter_by == "proposals":
            if q.isdigit():
                query = query.filter(func.coalesce(review_counts.c.reviewed_count, 0) >= int(q))
            query = query.order_by(func.coalesce(review_counts.c.reviewed_count, 0).desc())
        elif q:
            query = query.filter(
                (User.full_name.ilike(f"%{q}%")) |
                (User.email.ilike(f"%{q}%"))
            )

        if filter_by != "proposals":
            query = query.order_by(User.full_name.asc())

        reviewer_rows = query.all()

        for user, profile, reviewer, reviewed_count in reviewer_rows:
            reviewers.append({
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "profile_picture": profile.profile_picture,
                "reviewed_count": reviewed_count
            })

    return render_template(
        "hod_reviewers.html",
        prof=prof,
        reviewers=reviewers,
        department_name=department_name,
        q=q,
        filter_by=filter_by
    )

@app.route("/HOD/researchers")
@login_required
def hod_researchers():
    prof = get_profile(current_user.id)
    if not prof or prof.role != "HOD":
        flash("Access denied. HOD role required.", "error")
        return redirect(url_for("dashboard"))

    q = (request.args.get("q") or "").strip()
    filter_by = (request.args.get("filter") or "").strip().lower()
    department_name = (prof.department_name or "").strip()
    researchers = []
    if department_name:
        project_counts = (
            db.session.query(
                Project.researcher_id,
                func.count(Project.project_id).label("project_count")
            )
            .group_by(Project.researcher_id)
            .subquery()
        )

        query = (
            db.session.query(
                User,
                UserProfile,
                Researcher,
                func.coalesce(project_counts.c.project_count, 0).label("project_count")
            )
            .join(UserProfile, UserProfile.user_id == User.id)
            .join(Researcher, Researcher.user_id == User.id)
            .outerjoin(project_counts, project_counts.c.researcher_id == Researcher.researcher_id)
            .filter(
                func.lower(UserProfile.department_name) == department_name.lower(),
                UserProfile.role == "RESEARCHER"
            )
        )

        if filter_by == "name" and q:
            query = query.filter(User.full_name.ilike(f"%{q}%"))
        elif filter_by == "email" and q:
            query = query.filter(User.email.ilike(f"%{q}%"))
        elif filter_by == "projects":
            if q.isdigit():
                query = query.filter(func.coalesce(project_counts.c.project_count, 0) >= int(q))
            query = query.order_by(func.coalesce(project_counts.c.project_count, 0).desc())
        elif q:
            query = query.filter(
                (User.full_name.ilike(f"%{q}%")) |
                (User.email.ilike(f"%{q}%"))
            )

        if filter_by != "projects":
            query = query.order_by(User.full_name.asc())

        researcher_rows = query.all()

        for user, profile, researcher, project_count in researcher_rows:
            researchers.append({
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "profile_picture": profile.profile_picture,
                "project_count": project_count
            })

    return render_template(
        "hod_researchers.html",
        prof=prof,
        researchers=researchers,
        department_name=department_name,
        q=q,
        filter_by=filter_by
    )

@app.route("/HOD/user_profile/<user_id>")
@login_required
def user_profile(user_id):
    prof = get_profile(current_user.id)
    if not prof or prof.role != "HOD":
        flash("Access denied. HOD role required.", "error")
        return redirect(url_for("dashboard"))

    # Get the user profile to display
    user = User.query.filter_by(id=user_id).first()
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("hod_dashboard"))

    user_profile = get_profile(user_id)
    if not user_profile:
        flash("User profile not found.", "error")
        return redirect(url_for("hod_dashboard"))

    # Check if user is in the same department
    if user_profile.department_name != prof.department_name:
        flash("Access denied. User is not in your department.", "error")
        return redirect(url_for("hod_dashboard"))

    # Combine user and profile data
    profile_data = type('obj', (object,), {
        'full_name': user.full_name,
        'email': user.email,
        'role': user_profile.role,
        'department': user_profile.department_name,
        'phone': user_profile.contact_number,
        'address': user_profile.address,
        'emergency_contact_name': user_profile.emergency_contact_name,
        'emergency_contact_number': user_profile.emergency_contact_number,
        'profile_picture': user_profile.profile_picture
    })()

    # Get recent projects if the user is a researcher
    recent_projects = []
    researcher = get_researcher(user_id)
    if researcher:
        try:
            projects = (
                db.session.query(Project.project_id, Proposal.project_title)
                .join(Proposal, Proposal.proposal_id == Project.proposal_id)
                .filter(Project.researcher_id == researcher.researcher_id)
                .order_by(Project.start_date.desc())
                .limit(3)
                .all()
            )
            for project_id, project_title in projects:
                recent_projects.append({
                    'title': project_title,
                    'project_id': project_id
                })
        except Exception:
            # If query fails due to schema mismatch, just return empty list
            recent_projects = []

    return render_template(
        "user_profile.html",
        prof=prof,
        user_prof=profile_data,
        recent_projects=recent_projects
    )

#-------------------------
# REVIEWER ROUTES
#-------------------------
@app.route("/reviewer/dashboard")
@login_required
@reviewer_required
def reviewer_dashboard():
    rv = get_reviewer_by_user(current_user.id)
    if not rv:
        flash("Reviewer record missing. Contact admin.", "error")
        return redirect(url_for("dashboard"))

    pending = ReviewersAssignment.query.filter_by(
        reviewer_id=rv.reviewer_id, assignment_status="ASSIGNED"
    ).count()

    under_review = ReviewersAssignment.query.filter_by(
        reviewer_id=rv.reviewer_id, assignment_status="ACCEPTED"
    ).count()

    completed = Review.query.filter(Review.reviewer_id == rv.reviewer_id).count()

    recent_assignments = (ReviewersAssignment.query
        .filter_by(reviewer_id=rv.reviewer_id)
        .order_by(ReviewersAssignment.assigned_date.desc())
        .limit(5).all())

    recent_reviews = (Review.query
        .filter_by(reviewer_id=rv.reviewer_id)
        .order_by(Review.review_date.desc())
        .limit(5).all())

    return render_template(
        "reviewer_dashboard.html",
        pending=pending,
        under_review=under_review,
        completed=completed,
        recent_assignments=recent_assignments,
        recent_reviews=recent_reviews,
    )


@app.route("/reviewer/assignments")
@login_required
@reviewer_required
def reviewer_assigned_proposals():
    rv = get_reviewer_by_user(current_user.id)

    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "ALL").upper()

    query = (
        db.session.query(ReviewersAssignment, Proposal)
        .join(Proposal, Proposal.proposal_id == ReviewersAssignment.proposal_id)
        .filter(ReviewersAssignment.reviewer_id == rv.reviewer_id)
    )

    if status != "ALL":
        query = query.filter(db.func.upper(ReviewersAssignment.assignment_status) == status)

    if q:
        like = f"%{q}%"
        query = query.filter(Proposal.project_title.ilike(like))

    rows = query.order_by(ReviewersAssignment.assigned_date.desc()).all()

    return render_template("reviewer_assigned_proposals.html", rows=rows, q=q, status=status)



@app.route("/reviewer/assignments/view/<proposal_id>")
@login_required
@reviewer_required
def reviewer_assignment_view(proposal_id):
    rv = get_reviewer_by_user(current_user.id)

    # ensure this proposal is actually assigned to this reviewer
    row = (
        db.session.query(ReviewersAssignment, Proposal)
        .join(Proposal, Proposal.proposal_id == ReviewersAssignment.proposal_id)
        .filter(
            ReviewersAssignment.reviewer_id == rv.reviewer_id,
            Proposal.proposal_id == proposal_id
        )
        .first()
    )

    if not row:
        abort(404)

    assignment, proposal = row

    # format for your template (you used proposal.title/status)
    view_model = {
        "id": proposal.proposal_id,
        "title": proposal.project_title,
        "status": assignment.assignment_status.title(),  # ASSIGNED -> Assigned
        "abstract": proposal.abstract,
        "methodology": proposal.methodology,
        "assignment_status": assignment.assignment_status,  # raw
    }

    return render_template("reviewer_assignment_view.html", proposal=view_model)

@app.route("/reviewer/under-review")
@login_required
@reviewer_required
def reviewer_under_review():
    rv = get_reviewer_by_user(current_user.id)

    rows = (
        db.session.query(ReviewersAssignment, Proposal)
        .join(Proposal, Proposal.proposal_id == ReviewersAssignment.proposal_id)
        .filter(
            ReviewersAssignment.reviewer_id == rv.reviewer_id,
            ReviewersAssignment.assignment_status == "ACCEPTED"
        )
        .order_by(ReviewersAssignment.assigned_date.desc())
        .all()
    )

    return render_template("reviewer_under_review.html", rows=rows)

@app.route("/reviewer/guidelines")
@login_required
@reviewer_required
def reviewer_guidelines():
    return render_template("reviewer_guidelines.html")


@app.route("/reviewer/evaluate/<proposal_id>", methods=["GET", "POST"])
@login_required
@reviewer_required
def reviewer_evaluate(proposal_id):
    rv = get_reviewer_by_user(current_user.id)

    proposal = Proposal.query.get_or_404(proposal_id)

    # ensure reviewer is assigned
    assignment = ReviewersAssignment.query.filter_by(
        proposal_id=proposal_id,
        reviewer_id=rv.reviewer_id
    ).first_or_404()

    existing = Review.query.filter_by(
        proposal_id=proposal_id,
        reviewer_id=rv.reviewer_id
    ).first()

    submitted = existing is not None
    evaluated_at = existing.review_date.strftime("%d %b %Y, %I:%M %p") if existing else None

    if request.method == "POST":
        feedback = (request.form.get("feedback") or "").strip()
        recommendation = (request.form.get("recommendation") or "").upper()

        if not feedback:
            flash("Feedback cannot be empty.", "error")
            return redirect(request.url)

        if recommendation not in {"RECOMMENDED", "REVISION_REQUIRED", "REJECTED"}:
            flash("Invalid recommendation.", "error")
            return redirect(request.url)

        if existing:
            flash("This review has already been submitted.", "error")
            return redirect(request.url)

        review = Review(
            proposal_id=proposal_id,
            reviewer_id=rv.reviewer_id,
            feedback=feedback,
            recommendation=recommendation,
            review_date=datetime.now(timezone.utc)
        )

        db.session.add(review)
        db.session.flush()  # review now exists in the transaction (no early commit)

        # ---- Find targets ----
        researcher_user_id = get_researcher_user_id_from_proposal(proposal)
        hod_user_id = get_hod_user_id_for_proposal(proposal)
        admin_user_ids = get_all_admin_user_ids()

        # ---- Notify researcher ----
        if researcher_user_id:
            create_notification(
                user_id=researcher_user_id,
                message=f"A review was submitted for your proposal '{proposal.project_title}'.",
                notif_type="REVIEW",
                commit=False
            )

        # ---- Notify HoD ----
        if hod_user_id:
            create_notification(
                user_id=hod_user_id,
                message=f"A reviewer submitted feedback for '{proposal.project_title}'.",
                notif_type="REVIEW",
                commit=False
            )

        # ---- Notify admins ----
        for admin_user_id in admin_user_ids:
            create_notification(
                user_id=admin_user_id,
                message=f"Review submitted for '{proposal.project_title}'.",
                notif_type="REVIEW",
                commit=False
            )

        db.session.commit()


        flash("Review submitted successfully.", "success")
        return redirect(url_for("reviewer_under_review"))

    return render_template(
        "reviewer_evaluation.html",
        proposal=proposal,
        existing=existing,
        submitted=submitted,
        evaluated_at=evaluated_at
    )

@app.route("/reviewer/history")
@login_required
@reviewer_required
def reviewer_review_history():
    rv = get_reviewer_by_user(current_user.id)

    rows = (
        db.session.query(
            Proposal.proposal_id,
            Proposal.project_title,
            Review.recommendation,
            Review.review_date
        )
        .join(Review, Review.proposal_id == Proposal.proposal_id)
        .filter(Review.reviewer_id == rv.reviewer_id)
        .order_by(Review.review_date.desc())
        .all()
    )

    return render_template("reviewer_history.html", rows=rows)

@app.route("/reviewer/history/view/<proposal_id>")
@login_required
@reviewer_required
def reviewer_history_view(proposal_id):
    rv = get_reviewer_by_user(current_user.id)

    proposal = Proposal.query.get_or_404(proposal_id)

    review = Review.query.filter_by(
        proposal_id=proposal_id,
        reviewer_id=rv.reviewer_id
    ).first_or_404()

    status_map = {
        "RECOMMENDED": "Recommended",
        "REVISION_REQUIRED": "Revision Required",
        "REJECTED": "Rejected",
    }

    display_status = status_map.get(review.recommendation, "Unknown")

    return render_template(
        "reviewer_history_view.html",
        proposal=proposal,
        review=review,
        display_status=display_status,
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_user_profile_schema()
    app.run(debug=True)