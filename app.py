import os
from functools import wraps
from datetime import datetime, date, timedelta
import io
import csv

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import db, User, BusRoute, BusPass, Attendance, NewsNotice
from utils.email_helper import send_bus_email
from utils.excel_helper import parse_attendance_csv_or_excel, parse_student_enrollment_csv_or_excel

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'csmss-secret-key-12345')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///csmss_bus.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize Database
db.init_app(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# RBAC Decorator
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash("Unauthorized access! You do not have permissions for this page.", "danger")
                # Redirect to appropriate dashboard
                if current_user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif current_user.role == 'staff':
                    return redirect(url_for('staff_dashboard'))
                else:
                    return redirect(url_for('student_dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- PUBLIC PAGES ---

@app.route('/')
def home():
    routes = BusRoute.query.all()
    notices = NewsNotice.query.order_by(NewsNotice.created_at.desc()).limit(5).all()
    # Separate active delays for the alert banner
    delays = BusRoute.query.filter(BusRoute.status != 'On Time').all()
    return render_template('public/home.html', routes=routes, notices=notices, delays=delays)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f"Welcome back, {user.name}! Successfully logged in.", "success")
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'staff':
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('public/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash("Please fill in all required fields.", "warning")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Passwords do not match.", "warning")
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists. Please login instead.", "info")
            return redirect(url_for('login'))

        hashed_pass = generate_password_hash(password)
        new_user = User(
            name=name,
            email=email,
            phone=phone,
            password_hash=hashed_pass,
            role='student'  # Registration only available for students
        )
        db.session.add(new_user)
        try:
            db.session.commit()
            flash("Registration successful! You can now login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error registering user: {e}", "danger")

    return render_template('public/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been successfully logged out.", "success")
    return redirect(url_for('login'))

@app.route('/schedules')
def schedules():
    search_q = request.args.get('search', '').strip()
    if search_q:
        routes = BusRoute.query.filter(
            (BusRoute.route_name.icontains(search_q)) | 
            (BusRoute.bus_number.icontains(search_q)) |
            (BusRoute.via_points.icontains(search_q))
        ).all()
    else:
        routes = BusRoute.query.all()
    return render_template('public/schedules.html', routes=routes, search_q=search_q)

@app.route('/notices')
def notices_list():
    notices = NewsNotice.query.order_by(NewsNotice.created_at.desc()).all()
    return render_template('public/notices.html', notices=notices)

@app.route('/contact')
def contact():
    return render_template('public/contact.html')


# --- ADMIN DASHBOARD ---

@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    # Gather dashboard analytics data
    total_students = User.query.filter_by(role='student').count()
    total_staff = User.query.filter_by(role='staff').count()
    total_routes = BusRoute.query.count()
    total_passes = BusPass.query.count()
    active_passes = sum(1 for p in BusPass.query.all() if p.is_active)
    
    # Financial Analytics (Sales)
    pass_sales = BusPass.query.filter_by(payment_status='Paid').all()
    total_revenue = sum(p.price for p in pass_sales)

    # Monthly revenue distribution for charts
    monthly_sales = {}
    for p in pass_sales:
        month_str = p.created_at.strftime('%Y-%m')
        monthly_sales[month_str] = monthly_sales.get(month_str, 0) + p.price
    # Sort keys
    sorted_months = sorted(monthly_sales.keys())
    revenue_chart_data = {
        'labels': [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in sorted_months],
        'data': [monthly_sales[m] for m in sorted_months]
    }

    # Route delays
    delayed_routes = BusRoute.query.filter(BusRoute.status != 'On Time').count()

    # Pass types distribution
    pass_types = {'Monthly': 0, 'Quarterly': 0, 'Yearly': 0}
    for p in pass_sales:
        if p.pass_type in pass_types:
            pass_types[p.pass_type] += 1
            
    return render_template('admin/dashboard.html',
                           total_students=total_students,
                           total_staff=total_staff,
                           total_routes=total_routes,
                           active_passes=active_passes,
                           total_passes=total_passes,
                           total_revenue=total_revenue,
                           delayed_routes=delayed_routes,
                           revenue_chart=revenue_chart_data,
                           pass_types=pass_types)

# Admin Route Management (CRUD)
@app.route('/admin/routes')
@login_required
@role_required('admin')
def admin_routes():
    routes = BusRoute.query.all()
    return render_template('admin/routes_list.html', routes=routes)

@app.route('/admin/routes/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_route():
    if request.method == 'POST':
        name = request.form.get('route_name', '').strip()
        bus_num = request.form.get('bus_number', '').strip()
        via = request.form.get('via_points', '').strip()
        pickup = request.form.get('pickup_time', '').strip()
        dropoff = request.form.get('dropoff_time', '').strip()

        if not name or not bus_num or not via or not pickup or not dropoff:
            flash("All route fields are mandatory.", "warning")
            return redirect(url_for('admin_add_route'))

        new_route = BusRoute(
            route_name=name,
            bus_number=bus_num,
            via_points=via,
            pickup_time=pickup,
            dropoff_time=dropoff
        )
        db.session.add(new_route)
        try:
            db.session.commit()
            flash(f"Route '{name}' with Bus No. {bus_num} added successfully!", "success")
            return redirect(url_for('admin_routes'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding route: {e}", "danger")

    return render_template('admin/route_add.html')

@app.route('/admin/routes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_route(id):
    route = BusRoute.query.get_or_404(id)
    if request.method == 'POST':
        route.route_name = request.form.get('route_name', '').strip()
        route.bus_number = request.form.get('bus_number', '').strip()
        route.via_points = request.form.get('via_points', '').strip()
        route.pickup_time = request.form.get('pickup_time', '').strip()
        route.dropoff_time = request.form.get('dropoff_time', '').strip()
        route.status = request.form.get('status', 'On Time')
        route.delay_reason = request.form.get('delay_reason', '')

        # Trigger notification if status changes to delayed
        if route.status != 'On Time':
            # Notify registered students of delay
            students_on_route = User.query.filter_by(role='student').all() # simple demo notify all
            subject = f"Alert: CSMSS Bus Route {route.bus_number} Status Update"
            body = f"Dear student, we regret to inform you that Bus Route '{route.route_name}' (Bus No. {route.bus_number}) is currently <b>{route.status}</b> due to: {route.delay_reason or 'unspecified delay'}. Timings may fluctuate."
            for s in students_on_route:
                send_bus_email(s.email, subject, body)

        try:
            db.session.commit()
            flash(f"Route '{route.route_name}' updated successfully!", "success")
            return redirect(url_for('admin_routes'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating route: {e}", "danger")

    return render_template('admin/route_edit.html', route=route)

@app.route('/admin/routes/delete/<int:id>')
@login_required
@role_required('admin')
def admin_delete_route(id):
    route = BusRoute.query.get_or_404(id)
    db.session.delete(route)
    try:
        db.session.commit()
        flash("Route deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Cannot delete route. Error: {e}", "danger")
    return redirect(url_for('admin_routes'))

# Admin Staff Management (CRUD)
@app.route('/admin/staff')
@login_required
@role_required('admin')
def admin_staff():
    staff = User.query.filter_by(role='staff').all()
    return render_template('admin/staff_list.html', staff=staff)

@app.route('/admin/staff/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_staff():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        if not name or not email or not password:
            flash("Name, email, and password are required.", "warning")
            return redirect(url_for('admin_add_staff'))

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("User with this email already exists.", "warning")
            return redirect(url_for('admin_add_staff'))

        new_staff = User(
            name=name,
            email=email,
            phone=phone,
            password_hash=generate_password_hash(password),
            role='staff'
        )
        db.session.add(new_staff)
        try:
            db.session.commit()
            flash(f"Staff member '{name}' registered successfully!", "success")
            return redirect(url_for('admin_staff'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error registering staff: {e}", "danger")

    return render_template('admin/staff_add.html')

@app.route('/admin/staff/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_staff(id):
    staff = User.query.get_or_404(id)
    if request.method == 'POST':
        staff.name = request.form.get('name', '').strip()
        staff.phone = request.form.get('phone', '').strip()
        new_pass = request.form.get('password', '')
        if new_pass:
            staff.password_hash = generate_password_hash(new_pass)
        try:
            db.session.commit()
            flash(f"Staff '{staff.name}' updated successfully.", "success")
            return redirect(url_for('admin_staff'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating staff: {e}", "danger")
    return render_template('admin/staff_edit.html', staff=staff)

@app.route('/admin/staff/delete/<int:id>')
@login_required
@role_required('admin')
def admin_delete_staff(id):
    staff = User.query.get_or_404(id)
    db.session.delete(staff)
    try:
        db.session.commit()
        flash("Staff member deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {e}", "danger")
    return redirect(url_for('admin_staff'))

# Admin Student Directory
@app.route('/admin/students')
@login_required
@role_required('admin')
def admin_students():
    students = User.query.filter_by(role='student').all()
    return render_template('admin/students_list.html', students=students)

@app.route('/admin/students/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_student(id):
    student = User.query.get_or_404(id)
    if request.method == 'POST':
        student.name = request.form.get('name', '').strip()
        student.phone = request.form.get('phone', '').strip()
        new_pass = request.form.get('password', '')
        if new_pass:
            student.password_hash = generate_password_hash(new_pass)
        try:
            db.session.commit()
            flash(f"Student '{student.name}' updated successfully.", "success")
            return redirect(url_for('admin_students'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
    return render_template('admin/student_edit.html', student=student)

@app.route('/admin/students/delete/<int:id>')
@login_required
@role_required('admin')
def admin_delete_student(id):
    student = User.query.get_or_404(id)
    db.session.delete(student)
    try:
        db.session.commit()
        flash("Student deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {e}", "danger")
    return redirect(url_for('admin_students'))

# Admin Pass Management
@app.route('/admin/passes')
@login_required
@role_required('admin')
def admin_passes():
    passes = BusPass.query.order_by(BusPass.created_at.desc()).all()
    return render_template('admin/passes_list.html', passes=passes)

@app.route('/admin/passes/issue', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_issue_pass():
    students = User.query.filter_by(role='student').all()
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        pass_type = request.form.get('pass_type')
        duration = int(request.form.get('duration_months', 1))

        if not student_id or not pass_type:
            flash("All pass details are required.", "warning")
            return redirect(url_for('admin_issue_pass'))

        student = User.query.get(student_id)
        if not student:
            flash("Selected student not found.", "danger")
            return redirect(url_for('admin_issue_pass'))

        start = date.today()
        end = start + timedelta(days=30 * duration)
        price_mapping = {'Monthly': 500.0, 'Quarterly': 1400.0, 'Yearly': 5000.0}
        price = price_mapping.get(pass_type, 500.0) * (duration if pass_type == 'Monthly' else 1)

        new_pass = BusPass(
            student_id=student.id,
            pass_type=pass_type,
            start_date=start,
            end_date=end,
            price=price,
            payment_status='Paid',
            payment_id='MANUAL-ISSUE-' + datetime.utcnow().strftime('%Y%m%d%H%M%S'),
            receipt_url=f"manual_receipt_{student.id}.pdf"
        )
        db.session.add(new_pass)
        try:
            db.session.commit()
            
            # Send Notification email
            subject = "CSMSS College Bus Pass Issued Successfully"
            body = f"""<h3>Dear {student.name},</h3>
            <p>Your college bus pass has been issued manually by the Administrator.</p>
            <p><b>Pass Details:</b></p>
            <ul>
                <li>Pass Type: {pass_type}</li>
                <li>Valid From: {start}</li>
                <li>Valid Till: {end}</li>
                <li>Receipt Ref: {new_pass.payment_id}</li>
            </ul>
            <p>You can check the validity and access your receipt directly in your Student Dashboard.</p>
            <p>Regards,<br>Transport Cell, CSMSS CSCOE</p>"""
            send_bus_email(student.email, subject, body)

            flash(f"Bus pass issued successfully to {student.name}!", "success")
            return redirect(url_for('admin_passes'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")

    return render_template('admin/pass_issue.html', students=students)

# Admin Payments
@app.route('/admin/payments')
@login_required
@role_required('admin')
def admin_payments():
    payments = BusPass.query.filter(BusPass.payment_id.isnot(None)).order_by(BusPass.created_at.desc()).all()
    return render_template('admin/payments_list.html', payments=payments)

# Admin Notices Settings
@app.route('/admin/notices')
@login_required
@role_required('admin')
def admin_notices():
    notices = NewsNotice.query.order_by(NewsNotice.created_at.desc()).all()
    return render_template('admin/notices_list.html', notices=notices)

@app.route('/admin/notices/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_notice():
    routes = BusRoute.query.all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        route_id = request.form.get('route_id')

        if not title or not body:
            flash("Title and Body are required.", "warning")
            return redirect(url_for('admin_add_notice'))

        new_notice = NewsNotice(
            title=title,
            body=body,
            bus_route_id=int(route_id) if route_id else None,
            author_id=current_user.id
        )
        db.session.add(new_notice)
        try:
            db.session.commit()
            
            # Send Notification email to all students on notice addition
            students = User.query.filter_by(role='student').all()
            subject = f"CSMSS Notice: {title}"
            body_html = f"<h3>Notice Board Announcement:</h3><p>{body}</p><br>Regards,<br>CSMSS Admin Cell"
            for s in students:
                send_bus_email(s.email, subject, body_html)
                
            flash("Notice board announcement added and broadcasted to students!", "success")
            return redirect(url_for('admin_notices'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error publishing notice: {e}", "danger")

    return render_template('admin/notice_add.html', routes=routes)

@app.route('/admin/notices/delete/<int:id>')
@login_required
@role_required('admin')
def admin_delete_notice(id):
    notice = NewsNotice.query.get_or_404(id)
    db.session.delete(notice)
    try:
        db.session.commit()
        flash("Notice removed successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {e}", "danger")
    return redirect(url_for('admin_notices'))

# Admin Attendance Management
@app.route('/admin/attendance')
@login_required
@role_required('admin')
def admin_attendance():
    # Fetch latest 100 entries for review
    attendances = Attendance.query.order_by(Attendance.date.desc(), Attendance.id.desc()).limit(150).all()
    routes = BusRoute.query.all()
    return render_template('admin/attendance_report.html', attendances=attendances, routes=routes)

@app.route('/admin/attendance/import', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'staff')
def admin_import_attendance():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part provided.", "warning")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("No file selected.", "warning")
            return redirect(request.url)

        if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Parse file
            with open(filepath, 'rb') as f:
                success_count, errors = parse_attendance_csv_or_excel(f, filename, current_user.id)
            
            # Remove temporary uploaded file
            try:
                os.remove(filepath)
            except:
                pass

            if success_count > 0:
                flash(f"Successfully processed {success_count} attendance records!", "success")
            if errors:
                for err in errors[:5]: # Show top 5 errors to avoid flooding
                    flash(f"Error details: {err}", "danger")
            return redirect(url_for('admin_attendance') if current_user.role == 'admin' else url_for('staff_dashboard'))
        else:
            flash("Allowed file extensions are CSV or XLSX.", "warning")

    return render_template('admin/attendance_import.html')

@app.route('/admin/attendance/export')
@login_required
@role_required('admin')
def admin_export_attendance():
    """
    Exports all attendance records to a CSV file.
    """
    attendances = Attendance.query.order_by(Attendance.date.desc()).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # CSV Header
    writer.writerow(['Record ID', 'Student Name', 'Student Email', 'Bus Route', 'Bus Number', 'Date', 'Status', 'Marked By'])
    
    for att in attendances:
        writer.writerow([
            att.id,
            att.student.name,
            att.student.email,
            att.route.route_name,
            att.route.bus_number,
            att.date.strftime('%Y-%m-%d'),
            att.status,
            att.marker.name
        ])
        
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"CSMSS_Bus_Attendance_{date.today()}.csv"
    )

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_settings():
    # Mock system configurations editor
    if request.method == 'POST':
        flash("System configurations updated successfully!", "success")
        return redirect(url_for('admin_settings'))
    return render_template('admin/settings.html')


# --- STAFF DASHBOARD ---

@app.route('/staff')
@login_required
@role_required('staff')
def staff_dashboard():
    # Statistics for staff
    total_routes = BusRoute.query.count()
    student_count = User.query.filter_by(role='student').count()
    recent_notices = NewsNotice.query.filter_by(author_id=current_user.id).order_by(NewsNotice.created_at.desc()).limit(5).all()
    
    # Active delays posted by staff
    active_routes = BusRoute.query.all()
    
    return render_template('staff/dashboard.html', 
                           total_routes=total_routes, 
                           student_count=student_count, 
                           recent_notices=recent_notices,
                           active_routes=active_routes)

@app.route('/staff/students')
@login_required
@role_required('staff')
def staff_students():
    # Read-only student directory
    students = User.query.filter_by(role='student').all()
    return render_template('staff/students_list.html', students=students)

@app.route('/staff/attendance', methods=['GET', 'POST'])
@login_required
@role_required('staff', 'admin')
def staff_attendance():
    routes = BusRoute.query.all()
    students = User.query.filter_by(role='student').all()
    
    selected_route_id = request.args.get('route_id')
    selected_date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    
    route_students = []
    attendance_map = {}
    
    if selected_route_id:
        selected_route_id = int(selected_route_id)
        # We find students. For simplicity, since students aren't locked to single routes, we allow marking attendance for any student.
        route_students = students
        
        # Load existing attendance for this date & route
        existing_records = Attendance.query.filter_by(route_id=selected_route_id, date=selected_date).all()
        attendance_map = {att.student_id: att.status for att in existing_records}

    if request.method == 'POST':
        # Process attendance marks
        route_id = int(request.form.get('route_id'))
        attendance_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        
        # Parse status from checkboxes/radios
        for s in students:
            status = request.form.get(f"status_{s.id}", "Absent")
            
            existing = Attendance.query.filter_by(student_id=s.id, date=attendance_date).first()
            if existing:
                existing.status = status
                existing.route_id = route_id
                existing.marked_by = current_user.id
            else:
                new_att = Attendance(
                    student_id=s.id,
                    route_id=route_id,
                    date=attendance_date,
                    status=status,
                    marked_by=current_user.id
                )
                db.session.add(new_att)
                
        try:
            db.session.commit()
            flash("Attendance checklist updated successfully!", "success")
            return redirect(url_for('staff_attendance', route_id=route_id, date=attendance_date))
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving attendance: {e}", "danger")

    return render_template('staff/attendance_mark.html', 
                           routes=routes, 
                           students=route_students, 
                           selected_route_id=selected_route_id,
                           selected_date=selected_date_str,
                           attendance_map=attendance_map)

@app.route('/staff/attendance/log')
@login_required
@role_required('staff')
def staff_attendance_log():
    # Logs submitted by this staff member
    logs = Attendance.query.filter_by(marked_by=current_user.id).order_by(Attendance.date.desc(), Attendance.id.desc()).all()
    return render_template('staff/attendance_log.html', logs=logs)

@app.route('/staff/notices', methods=['GET', 'POST'])
@login_required
@role_required('staff')
def staff_notices():
    routes = BusRoute.query.all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        route_id = request.form.get('route_id')

        if not title or not body:
            flash("Title and Body are required.", "warning")
            return redirect(url_for('staff_notices'))

        new_notice = NewsNotice(
            title=title,
            body=body,
            bus_route_id=int(route_id) if route_id else None,
            author_id=current_user.id
        )
        db.session.add(new_notice)
        
        # Update route status directly if specified
        if route_id:
            route = BusRoute.query.get(int(route_id))
            if route:
                route.status = "Delayed"
                route.delay_reason = title

        try:
            db.session.commit()
            
            # Send Notification email to students on notice addition
            students = User.query.filter_by(role='student').all()
            subject = f"CSMSS Bus Update: {title}"
            body_html = f"<h3>Notice Board Announcement:</h3><p>{body}</p><br>Regards,<br>CSMSS Transport Cell"
            for s in students:
                send_bus_email(s.email, subject, body_html)
                
            flash("Route status announcement added successfully!", "success")
            return redirect(url_for('staff_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error publishing: {e}", "danger")

    return render_template('staff/notice_create.html', routes=routes)

@app.route('/staff/profile', methods=['GET', 'POST'])
@login_required
@role_required('staff', 'student')
def user_profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', '').strip()
        current_user.phone = request.form.get('phone', '').strip()
        
        new_pass = request.form.get('password', '')
        confirm_pass = request.form.get('confirm_password', '')
        if new_pass:
            if new_pass != confirm_pass:
                flash("Passwords do not match.", "warning")
                return redirect(url_for('user_profile'))
            current_user.password_hash = generate_password_hash(new_pass)
            
        try:
            db.session.commit()
            flash("Profile details updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
            
    return render_template('public/profile.html')


# --- STUDENT DASHBOARD ---

@app.route('/student')
@login_required
@role_required('student')
def student_dashboard():
    # Load student active and previous passes
    passes = BusPass.query.filter_by(student_id=current_user.id).order_by(BusPass.created_at.desc()).all()
    active_pass = None
    for p in passes:
        if p.is_active:
            active_pass = p
            break
            
    # Load recent 10 attendances
    attendances = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).limit(15).all()
    
    # Calculate attendance percentage
    total_att = len(attendances)
    present_att = sum(1 for a in attendances if a.status == 'Present')
    att_percent = (present_att / total_att * 100) if total_att > 0 else 100.0

    return render_template('student/dashboard.html', 
                           passes=passes, 
                           active_pass=active_pass, 
                           attendances=attendances, 
                           att_percent=att_percent)

@app.route('/student/buy-pass')
@login_required
@role_required('student')
def student_buy_pass():
    # Display purchase options
    pass_options = [
        {'type': 'Monthly', 'price': 500.0, 'description': 'Valid for 30 days from date of payment.'},
        {'type': 'Quarterly', 'price': 1400.0, 'description': 'Save ₹100. Valid for 90 days.'},
        {'type': 'Yearly', 'price': 5000.0, 'description': 'Full academic year pass. Save ₹1000.'}
    ]
    return render_template('student/buy_pass.html', pass_options=pass_options)

@app.route('/student/process-payment', methods=['POST'])
@login_required
@role_required('student')
def student_process_payment():
    pass_type = request.form.get('pass_type')
    price = float(request.form.get('price', 500.0))
    payment_method = request.form.get('payment_method', 'Razorpay Sim')
    
    # Verify values
    if not pass_type:
        return jsonify({'success': False, 'message': 'Invalid pass selection.'}), 400
        
    # Calculate dates
    start = date.today()
    duration_days = 30
    if pass_type == 'Quarterly':
        duration_days = 90
    elif pass_type == 'Yearly':
        duration_days = 365
        
    end = start + timedelta(days=duration_days)
    
    # Simulate Payment Verification
    mock_payment_id = f"PAY-{pass_type.upper()}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    new_pass = BusPass(
        student_id=current_user.id,
        pass_type=pass_type,
        start_date=start,
        end_date=end,
        price=price,
        payment_status='Paid',
        payment_id=mock_payment_id,
        receipt_url=f"receipt_{mock_payment_id}.pdf"
    )
    
    db.session.add(new_pass)
    try:
        db.session.commit()
        
        # Send transactional confirmation email
        subject = "Receipt: Your CSMSS College Bus Pass Purchase"
        body = f"""<h3>Dear {current_user.name},</h3>
        <p>Your payment of ₹{price} for the <b>{pass_type}</b> bus pass was processed successfully.</p>
        <p><b>Transaction & Validity Details:</b></p>
        <ul>
            <li>Pass ID: {new_pass.id}</li>
            <li>Transaction ID: {mock_payment_id}</li>
            <li>Validity Start: {start}</li>
            <li>Validity End: {end}</li>
            <li>Status: SUCCESS</li>
        </ul>
        <p>You can view and print this receipt from your dashboard's Billing page.</p>
        <p>Thank you,<br>CSMSS Transport Cell</p>"""
        send_bus_email(current_user.email, subject, body)
        
        return jsonify({
            'success': True,
            'message': 'Payment successful! Your bus pass has been activated.',
            'receipt_id': new_pass.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error processing transaction: {e}'}), 500

@app.route('/student/receipt/<int:id>')
@login_required
@role_required('student', 'admin')
def student_receipt(id):
    bus_pass = BusPass.query.get_or_404(id)
    # Check authorization (students can only see their own receipts, Admin can see all)
    if current_user.role == 'student' and bus_pass.student_id != current_user.id:
        flash("Unauthorized access to receipt.", "danger")
        return redirect(url_for('student_dashboard'))
        
    return render_template('student/receipt.html', bus_pass=bus_pass)

@app.route('/student/routes')
@login_required
@role_required('student')
def student_routes():
    # Reuse schedule view inside dashboard structure
    routes = BusRoute.query.all()
    return render_template('student/routes_view.html', routes=routes)


# --- CONTEXT PROCESSOR FOR BRANDING ---
@app.context_processor
def inject_branding():
    return {
        'college_name': 'CSMSS Chhatrapati Shahu College of Engineering',
        'college_address': 'Kanchanwadi, Paithan Road, Chhatrapati Sambhajinagar (Aurangabad), Maharashtra',
        'current_year': datetime.now().year
    }

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
