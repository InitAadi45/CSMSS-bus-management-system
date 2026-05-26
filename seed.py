import os
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
from app import app
from models import db, User, BusRoute, BusPass, Attendance, NewsNotice

def seed_database():
    print("Initializing Database Seeder...")
    
    # Ensure tables are created
    db.drop_all()
    db.create_all()
    print("Database tables recreated successfully.")
    
    # 1. Create Users
    print("Seeding Users...")
    users_data = [
        # Admins
        {
            "name": "CSMSS Admin Team",
            "email": "aadi45@gmail.com",
            "password": "Aadi@4555",
            "role": "admin",
            "phone": "9876543210"
        },
        # Staff
        {
            "name": "Pranav Pakhale (Transport Head)",
            "email": "pranav123@gmail.com",
            "password": "pranav123",
            "role": "staff",
            "phone": "9604448770"
        },
        {
            "name": "Mohit Kalwaghe(Bus In-Charge)",
            "email": "mohit123@gmail.com",
            "password": "mohit123",
            "role": "staff",
            "phone": "8888823456"
        },
        # Students
        {
            "name": "Kedar Tagalpallewar",
            "email": "kedar123@gmail.com",
            "password": "kedar123",
            "role": "student",
            "phone": "7777712345"
        },
        {
            "name": "Ashish Kamble",
            "email": "ashish123@gmail.com",
            "password": "ashish123",
            "role": "student",
            "phone": "7777723456"
        },
        {
            "name": "Kailas Jadhav",
            "email": "kailas123@gmail.com",
            "password": "kailas123",
            "role": "student",
            "phone": "7777734567"
        }
    ]
    
    seeded_users = {}
    for user_info in users_data:
        new_user = User(
            name=user_info["name"],
            email=user_info["email"],
            password_hash=generate_password_hash(user_info["password"]),
            role=user_info["role"],
            phone=user_info["phone"]
        )
        db.session.add(new_user)
        seeded_users[user_info["email"]] = new_user
        
    db.session.commit()
    print("Users seeded successfully.")

    # 2. Create Bus Routes
    print("Seeding Bus Routes...")
    routes_data = [
        {
            "route_name": "CIDCO - Kranti Chowk - Station - Campus",
            "bus_number": "MH-20-EF-1234",
            "via_points": "CIDCO Bus Stand, Cannaught Place, Kranti Chowk, Railway Station, Kanchanwadi",
            "pickup_time": "07:30 AM",
            "dropoff_time": "05:30 PM",
            "status": "On Time",
            "delay_reason": None
        },
        {
            "route_name": "Paithan - Bidkin - Campus",
            "bus_number": "MH-20-EF-5678",
            "via_points": "Paithan Bus Stand, Bidkin Chowk, Dhoregaon, Chittegaon, Kanchanwadi",
            "pickup_time": "07:15 AM",
            "dropoff_time": "05:45 PM",
            "status": "Delayed",
            "delay_reason": "Heavy traffic construction near Bidkin highway bypass"
        },
        {
            "route_name": "Waluj - Bajajnagar - Campus",
            "bus_number": "MH-20-EF-9012",
            "via_points": "Waluj Industrial Area, Bajajnagar Chowk, AS Club, Tisgaon Naka, Kanchanwadi",
            "pickup_time": "07:45 AM",
            "dropoff_time": "05:15 PM",
            "status": "On Time",
            "delay_reason": None
        },
        {
            "route_name": "Garkheda - Sutgirni - Campus",
            "bus_number": "MH-20-EF-3456",
            "via_points": "Garkheda Stadium, Sutgirni Chowk, Gajanan Temple, Peer Bazar, Kanchanwadi",
            "pickup_time": "08:00 AM",
            "dropoff_time": "05:00 PM",
            "status": "On Time",
            "delay_reason": None
        }
    ]
    
    seeded_routes = []
    for r_data in routes_data:
        new_route = BusRoute(
            route_name=r_data["route_name"],
            bus_number=r_data["bus_number"],
            via_points=r_data["via_points"],
            pickup_time=r_data["pickup_time"],
            dropoff_time=r_data["dropoff_time"],
            status=r_data["status"],
            delay_reason=r_data["delay_reason"]
        )
        db.session.add(new_route)
        seeded_routes.append(new_route)
        
    db.session.commit()
    print("Bus Routes seeded successfully.")

    # 3. Create News Notices
    print("Seeding News & Notices...")
    admin_user = seeded_users["admin@csmss.edu"]
    staff_user = seeded_users["staff@csmss.edu"]
    
    notices_data = [
        {
            "title": "Semester Pass Renewal Phase 2",
            "body": "All regular student commuters are hereby notified that the bus pass renewal window for the upcoming semester is open. Students must renew their passes online by the end of this month to ensure uninterrupted service on all lines.",
            "bus_route_id": None,
            "author_id": admin_user.id
        },
        {
            "title": "Route 2 - Bidkin Delay Alert",
            "body": "The Paithan-Bidkin route bus (MH-20-EF-5678) is running late by approximately 20 minutes due to ongoing highway extension construction work near Bidkin town. Students are advised to wait at designated stops.",
            "bus_route_id": seeded_routes[1].id, # Paithan route
            "author_id": staff_user.id
        },
        {
            "title": "Revised Timings for Waluj Route",
            "body": "Starting next Monday, the Waluj route bus pickup timing will be shifted 15 minutes earlier (07:30 AM instead of 07:45 AM) to accommodate students appearing for early semester exams.",
            "bus_route_id": seeded_routes[2].id, # Waluj route
            "author_id": staff_user.id
        }
    ]
    
    for n_data in notices_data:
        new_notice = NewsNotice(
            title=n_data["title"],
            body=n_data["body"],
            bus_route_id=n_data["bus_route_id"],
            author_id=n_data["author_id"]
        )
        db.session.add(new_notice)
        
    db.session.commit()
    print("News Notices seeded successfully.")

    # 4. Create Bus Passes (Active & Expired)
    print("Seeding Bus Passes...")
    student_1 = seeded_users["student@csmss.edu"]
    student_2 = seeded_users["rahul.sharma@csmss.edu"]
    # student_3 (priya.deshmukh) has no pass (to verify empty state)

    today = date.today()
    
    passes_data = [
        # Student 1: Active Pass
        {
            "student_id": student_1.id,
            "pass_type": "Monthly",
            "start_date": today - timedelta(days=10),
            "end_date": today + timedelta(days=20),
            "price": 500.0,
            "payment_status": "Paid",
            "payment_id": "PAY-MONTHLY-SEEDED101",
            "receipt_url": "receipt_PAY-MONTHLY-SEEDED101.pdf"
        },
        # Student 1: Expired Pass
        {
            "student_id": student_1.id,
            "pass_type": "Monthly",
            "start_date": today - timedelta(days=41),
            "end_date": today - timedelta(days=11),
            "price": 500.0,
            "payment_status": "Paid",
            "payment_id": "PAY-MONTHLY-SEEDED100",
            "receipt_url": "receipt_PAY-MONTHLY-SEEDED100.pdf"
        },
        # Student 2: Active Yearly Pass
        {
            "student_id": student_2.id,
            "pass_type": "Yearly",
            "start_date": today - timedelta(days=50),
            "end_date": today + timedelta(days=315),
            "price": 5000.0,
            "payment_status": "Paid",
            "payment_id": "PAY-YEARLY-SEEDED201",
            "receipt_url": "receipt_PAY-YEARLY-SEEDED201.pdf"
        }
    ]
    
    for p_data in passes_data:
        new_pass = BusPass(
            student_id=p_data["student_id"],
            pass_type=p_data["pass_type"],
            start_date=p_data["start_date"],
            end_date=p_data["end_date"],
            price=p_data["price"],
            payment_status=p_data["payment_status"],
            payment_id=p_data["payment_id"],
            receipt_url=p_data["receipt_url"]
        )
        db.session.add(new_pass)
        
    db.session.commit()
    print("Bus Passes seeded successfully.")

    # 5. Create Attendance Records
    print("Seeding Attendance Logs...")
    
    # Create attendance for Student 1 and Student 2 over the past 12 days
    route_s1 = seeded_routes[0]  # CIDCO Route
    route_s2 = seeded_routes[2]  # Waluj Route
    
    for i in range(12):
        log_date = today - timedelta(days=i)
        # Skip Sundays
        if log_date.weekday() == 6:
            continue
            
        # Student 1: Mostly Present
        status_s1 = "Present" if i != 3 and i != 8 else "Absent"
        att_s1 = Attendance(
            student_id=student_1.id,
            route_id=route_s1.id,
            date=log_date,
            status=status_s1,
            marked_by=staff_user.id
        )
        db.session.add(att_s1)
        
        # Student 2: Always Present
        att_s2 = Attendance(
            student_id=student_2.id,
            route_id=route_s2.id,
            date=log_date,
            status="Present",
            marked_by=staff_user.id
        )
        db.session.add(att_s2)
        
    db.session.commit()
    print("Attendance logs seeded successfully.")
    
    print("\nDatabase seeding completed successfully!")
    print("Admin:   email: admin@csmss.edu   password: admin123")
    print("Staff:   email: staff@csmss.edu   password: staff123")
    print("Student: email: student@csmss.edu password: student123")

if __name__ == '__main__':
    with app.app_context():
        seed_database()
