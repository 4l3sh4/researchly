from flask import Flask, render_template, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from datetime import datetime, timezone
import uuid

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'A&WGirlies'

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
    user_id = db.Column(
        db.String(36),
        db.ForeignKey('user.id'),
        primary_key=True
    )
    contact_number = db.Column(db.String(15), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    emergency_contact_name = db.Column(db.String(80), nullable=False)
    emergency_contact_number = db.Column(db.String(15), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
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
        db.ForeignKey('bankaccount.bank_account_number')
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
        db.ForeignKey('grantscheme.scheme_id'),
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
        db.ForeignKey('grantscheme.scheme_id'),
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
    return User.query.get(int(user_id))


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


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    error_message = None

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                error_message = "Invalid password. Please try again."
        else:
            error_message = "This email has not registered. Please try again."

    return render_template('login.html', form=form, error_message=error_message)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    return render_template('edit_profile.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit(): 
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(email=form.email.data, full_name=form.full_name.data, password=hashed_pw)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('edit_profile'))

    return render_template('register.html', form=form)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
