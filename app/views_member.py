from app import app
from flask import flash, redirect, render_template, url_for
from flask import request
from flask import session
import functools
import math
import re
from datetime import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from app.config.database import getCursor, getDbConnection
from app.config.helpers import require_role, format_date
import os
from app.config.database import getCursor, getDbConnection
from app.config.helpers import require_role
from app.config.models import get_all_workshops
from app.config.helpers import format_date

dir_path = os.path.dirname(os.path.realpath(__file__))







  #on-screen notification function added
def reminder():   
    current_time = date.today()
    print(current_time)
    #get the member's userID
    username = session.get('username')
    cur = getCursor()
    cur.execute("SELECT * FROM Users where Username = %s;",(username,))
    user =cur.fetchone()      
    #find the member's description finish dat
    cur = getCursor()
    sql = """
        SELECT 
                  s.*
                  FROM Subscriptions s
                  WHERE MemberID = %s
                  AND DATEDIFF(s.EndDate, CURDATE()) BETWEEN 0 AND 7
                  AND s.subscriptionStatus = 'Active';
        """
    cur.execute(sql,(user[0],))
    sub = cur.fetchone()
    print(sub)
    if sub:
        print(sub[5])
        expired_time = sub[5]
        time_difference = expired_time - current_time
        if time_difference.days<= 7:
            flash(f"Your subscription will be expired in {time_difference.days} days! Please renew your subscription.",'danger')
        if sub[9]=="Yes":
            print(sub[9])
            msg =  "You have received a message from manager"
            return msg

@app.route('/member')
def member_dashboard():
    if 'loggedin' in session and session['role'] == 1:
        msg = reminder()
     
        return render_template('dashboard/member_dashboard.html', username=session['username'],msg = msg)
    return redirect(url_for('login'))
                    
# update member's info
@app.route('/update/info/member' , methods=['GET', 'POST'])
def update_info_member():
    msg = ""
    username = session.get('username')
    cur = getCursor()
    cur.execute("SELECT * FROM Users where Username = %s;",(username,))
    user = cur.fetchone()
    cur = getCursor()
    cur.execute("SELECT * FROM MemberProfiles where UserID = %s;",(user[0],))
    member = cur.fetchone()
    if request.method =='POST':
        title = request.form.get('title')
        first_name = request.form.get('firstname')
        family_name = request.form.get('familyname')
        position = request.form.get('position')
        phone = request.form.get('phonenumber')
        email = request.form.get('email')
        address =request.form.get('address')
        date_of_birth = request.form.get('DoB')

    # optional breeding info  
        if 'breeding'not in request.form:
            breeding = None
        else:
            breeding = request.form.get('breeding')

        #validation for name
        pattern = re.compile("^[A-Za-z]+$")
        if pattern.match(first_name) and pattern.match(family_name):
        #update into Users table   
            cur = getCursor()
            sql = """
            UPDATE MemberProfiles 
            SET Title = %s,
                FirstName = %s,
                FamilyName = %s,
                Position = %s,
                PhoneNumber = %s,
                Email = %s,
                Address = %s,
                DateOfBirth = %s,
                
            
                MerinoBreedingDetails =COALESCE(%s, MerinoBreedingDetails)
            WHERE UserID = %s;
            
            """
            cur.execute(sql, (
                title,
                first_name,
                family_name,
                position,
                phone, 
                email,
                address, 
                date_of_birth, 
                breeding, 
                user[0]))
           


            flash('Information Updated','succes')
            return redirect(url_for('update_info_member'))
        else:
            flash('Please make sure your inputs for names are only letters','danger')
            return render_template('updateinfo.html', msg=msg, member=member, form_action = '/update/info/member')
    else:
        return render_template('updateinfo.html', msg=msg, member=member, form_action = '/update/info/member')
        







@app.route('/lesson/details/<int:lesson_id>')
@require_role(1)
def lesson_details(lesson_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    # Only show lesson that hasn't been booked
    cursor.execute("""
    SELECT l.*, lt.Name AS LessonType, lt.Description,
            t.FirstName AS TutorFirstName, t.FamilyName AS TutorFamilyName,
            t.ProfileImage AS TutorProfileImage
    FROM OneOnOneLessons l
    JOIN LessonTypes lt ON l.LessonTypeID = lt.LessonTypeID
    JOIN TutorProfiles t ON l.TutorID = t.UserID
    WHERE l.LessonID = %s AND l.IsBooked = FALSE
    """, (lesson_id,))
    
    lesson_details = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if not lesson_details:
        flash('Lesson not found.', 'danger')
        return redirect(url_for('member_dashboard'))  # Redirect to a dashboard or relevant page if lesson is not found
    
    return render_template('member/lesson_details.html', lesson=lesson_details, format_date = format_date)

@app.route('/book_lesson', methods=['POST'])
@require_role(1)
def book_lesson():
    lesson_id = request.form.get('lesson_id')
    member_id = session.get('id')

    try:
        connection = getDbConnection()
        cursor = connection.cursor(dictionary=True)

        # Retrieve lesson cost for payment record.
        cursor.execute("""
            SELECT Cost FROM OneOnOneLessons WHERE LessonID = %s
        """, (lesson_id,))
        lesson = cursor.fetchone()
        lesson_cost = lesson['Cost'] if lesson else 0

        # Update the lesson as booked
        cursor.execute("""
            UPDATE OneOnOneLessons
            SET IsBooked = TRUE
            WHERE LessonID = %s
        """, (lesson_id,))

        # Create a booking record
        cursor.execute("""
            INSERT INTO Bookings (MemberID, LessonID, BookingDate, CreatedAt, Status)
            VALUES (%s, %s, NOW(), NOW(),'Confirmed')
        """, (member_id, lesson_id))

        booking_id = cursor.lastrowid
        # Create a payment record for booking the lesson
        cursor.execute("""
            INSERT INTO Payments (MemberID, BookingID, Amount, Date, CreatedAt, Type)
            VALUES (%s, %s, %s, NOW(), NOW(), 'Lesson')
        """, (member_id, booking_id, lesson_cost))

        connection.commit()
        flash('Lesson booked and payment processed successfully!', 'success')
    except Exception as e:
        connection.rollback()
        flash('An error occurred during booking or payment processing.', 'danger')
        print(e)
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('my_bookings', lesson_id=lesson_id))

@app.route('/my_bookings')
@require_role(1)
def my_bookings():
    
    member_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    print(member_id)
    cursor.execute("""
        SELECT b.BookingID, b.Status, b.BookingDate, 
               CASE 
                   WHEN b.WorkshopID IS NOT NULL THEN (SELECT Title FROM Workshops w WHERE w.WorkshopID = b.WorkshopID)
                   WHEN b.LessonID IS NOT NULL THEN (SELECT lt.Name FROM OneOnOneLessons l JOIN LessonTypes lt ON l.LessonTypeID = lt.LessonTypeID WHERE l.LessonID = b.LessonID)
               END AS BookingType,
               CASE 
                   WHEN b.WorkshopID IS NOT NULL THEN 'Workshop'
                   WHEN b.LessonID IS NOT NULL THEN 'One-on-One Lesson'
               END AS BookingCategory
        FROM Bookings b
        WHERE b.MemberID = %s
        ORDER BY b.BookingDate DESC
    """, (member_id,))
    
    bookings = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('member/my_bookings.html', bookings=bookings)

@app.route('/booking_details/<int:booking_id>')
@require_role(1)
def booking_details(booking_id):
    member_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    # Fetch general booking information
    cursor.execute("""
        SELECT b.BookingID, b.Status, b.BookingDate, 
               CASE 
                   WHEN b.WorkshopID IS NOT NULL THEN 'Workshop'
                   WHEN b.LessonID IS NOT NULL THEN 'One-on-One Lesson'
               END AS BookingCategory,
               b.WorkshopID, b.LessonID
        FROM Bookings b
        WHERE b.BookingID = %s AND b.MemberID = %s
    """, (booking_id, member_id))

    booking = cursor.fetchone()

    # Fetch specific details based on booking type
    details = None
    if booking and booking['WorkshopID']:
        cursor.execute("""
            SELECT w.Title, w.Details, w.Location, w.Date, w.Time, w.Cost
            FROM Workshops w
            WHERE w.WorkshopID = %s
        """, (booking['WorkshopID'],))
        details = cursor.fetchone()
        details['Type'] = 'Workshop'
    elif booking and booking['LessonID']:
        cursor.execute("""
            SELECT l.Date, l.StartTime, l.EndTime, l.Location, l.Cost, lt.Name AS LessonType, lt.Description
            FROM OneOnOneLessons l
            JOIN LessonTypes lt ON l.LessonTypeID = lt.LessonTypeID
            WHERE l.LessonID = %s
        """, (booking['LessonID'],))
        details = cursor.fetchone()
        details['Type'] = 'One-on-One Lesson'

    cursor.close()
    connection.close()

    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('member_dashboard'))

    return render_template('member/booking_details.html', booking=booking, details=details)

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@require_role(1)
def cancel_booking(booking_id):
    member_id = session.get('id')

    try:
        connection = getDbConnection()
        cursor = connection.cursor(dictionary=True)

        # Retrieve the booking to determine if it's a workshop or lesson booking
        cursor.execute("""
            SELECT WorkshopID, LessonID FROM Bookings 
            WHERE BookingID = %s AND MemberID = %s
        """, (booking_id, member_id))
        booking = cursor.fetchone()

        if booking:
            # Update booking status to 'Cancelled'
            cursor.execute("""
                UPDATE Bookings SET Status = 'Cancelled' WHERE BookingID = %s
            """, (booking_id,))

            if booking['LessonID']:
                # If it's a lesson, make the lesson available again
                cursor.execute("""
                    UPDATE OneOnOneLessons SET IsBooked = FALSE WHERE LessonID = %s
                """, (booking['LessonID'],))

            connection.commit()
            flash('Booking cancelled successfully.', 'success')
        else:
            flash('Booking not found.', 'danger')

    except Exception as e:
        connection.rollback()
        flash('An error occurred during the cancellation process.', 'danger')
        print(e)

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('my_bookings'))


@app.route("/view_tutorprofile")
def view_tutorprofile():
    connection = getCursor()
    connection.execute(f"""
                       SELECT
                        UserID AS TutorID,
                        CONCAT(Title, ' ', FirstName, ' ', FamilyName) AS Name,
                        Position,
                        PhoneNumber AS Phone,
                        Email,
                        TutorProfile AS Profile,
                        ProfileImage AS Image
                        FROM
                        TutorProfiles;
                        """)
    view_tutorprofile = connection.fetchall()
    print(view_tutorprofile)
    return render_template("member/view_tutorprofile.html", view_tutorprofile=view_tutorprofile)


@app.route("/tutor_lessons/<int:tutorid>")
def tutor_lessons(tutorid):
    connection = getCursor()
    connection.execute("""
                       SELECT
                           lt.Name AS LessonName,
                           ool.Date AS BookingDate,
                           ool.StartTime,
                           ool.EndTime,
                           ool.Location,
                           ool.Cost,
                           ool.LessonID
                       FROM
                           OneOnOneLessons ool
                           JOIN LessonTypes lt ON ool.LessonTypeID = lt.LessonTypeID
                       WHERE
                           ool.TutorID = %s
                           AND ool.IsBooked = FALSE;
                       """, (tutorid,))
    tutor_lessons = connection.fetchall()
    print(tutor_lessons)
    return render_template("member/tutor_lessons.html", tutorid=tutorid, tutor_lessons=tutor_lessons, format_date=format_date)







@app.route("/subscription")
def subscription():
    cursor = getCursor()
    cursor.execute('SELECT * FROM Subscriptions WHERE MemberID = %s', (session['id'],))
    subdetails = cursor.fetchone()
    cursor.fetchall()

    cursor.execute('SELECT * FROM Payments WHERE Type = "Subscription" and MemberID = %s;', (session['id'],))
    paymentsdetails = cursor.fetchall()

    today = datetime.now().date()

    return render_template("member/subscriptionDetail.html", subdetails = subdetails, paymentsdetails = paymentsdetails, today = today, format_date = format_date )


@app.route("/cancelsubscription")
def cancelsubscription():
    cursor = getCursor()
    cursor.execute('UPDATE Subscriptions SET  subscriptionStatus = "Cancelled"  WHERE MemberID = %s ;', ( session['id'],))
    return redirect("/subscription")


@app.route("/renewsubscription", methods=["get", "post"])
def renewsubscription():
    cursor = getCursor()
    cursor.execute('SELECT * FROM SubscriptionPrices;')
    prices = cursor.fetchall()
    annualfee = prices[0][1]
    monthlyfee = prices[1][1]
    discountfee = prices[2][1]

    if request.method == 'POST':
        memberID = session['id']
        subscription = request.form['subscription']
        startdate = request.form['startdate']
        startdate = datetime.strptime(startdate, "%Y-%m-%d").date()
        amount = request.form['fee']
        months = int(request.form['months'],0)

        today = datetime.now().date()
        cursor = getCursor()
        cursor.execute('SELECT StartDate,EndDate FROM Subscriptions WHERE MemberID = %s;', (session['id'],))
        originalsubscription = cursor.fetchone()
      
        originalstart = originalsubscription[0]
        originalenddate = originalsubscription[1]
        
        print(originalenddate)
        if today < originalenddate: #extend
            updatestartdate = originalstart
        else: #expired
            updatestartdate = startdate
        print(updatestartdate)

        if subscription == 'Annual':
            fee = annualfee
            if request.form.get('discount') == "on":
                discount =(discountfee/100) * annualfee
            else:
                discount = 0.00
            enddate = startdate + relativedelta(months=12)
        else:
            fee = monthlyfee
            if request.form.get('discount') == "on":
                discount =(discountfee/100) * monthlyfee
            else:
                discount = 0.00
            enddate = startdate + relativedelta(months=months)            

        cursorID=getCursor()
        cursorID.execute('UPDATE Subscriptions SET Type = %s, Fee = %s, Discount = %s, StartDate = %s, EndDate = %s, subscriptionStatus = "Active" WHERE MemberID = %s ;', \
                         (subscription,fee,discount,updatestartdate, enddate, memberID,))
        
        cursorSubID = getCursor()
        cursorSubID.execute('SELECT SubscriptionID FROM Subscriptions WHERE MemberID = %s;', (memberID,))
        SubID = cursorSubID.fetchone()[0]
        cursorSubID.fetchall()

        paymentdate = datetime.now()
        cursorSubID.execute('INSERT INTO Payments(MemberID, SubscriptionID, BookingID, Amount, Date, CreatedAt, Type) VALUES( \
                       %s, %s, NULL, %s, %s, %s, "Subscription");', (memberID, SubID, amount, paymentdate.date(), paymentdate, ))
        return redirect("/subscription")

            
    else:
        today = datetime.now().date()
        cursor = getCursor()
        cursor.execute('SELECT EndDate FROM Subscriptions WHERE MemberID = %s;', (session['id'],))
        enddate = cursor.fetchone()[0]
        if today <= enddate: #extend
            return render_template("member/renewsubscription.html", defaultdate = enddate, annualfee = annualfee, monthlyfee=monthlyfee,discountfee=discountfee  )
        else: #expired
            return render_template("member/renewsubscription.html", defaultdate = today, annualfee = annualfee, monthlyfee=monthlyfee,discountfee=discountfee)

        
# Booking and Searching for a workshop
@app.route("/workshops/book") 
def book_workshop():
        connection = getDbConnection()
        cursor = connection.cursor(dictionary=True)

        search_query = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Set the number of items per page

        query_base = """
        FROM Workshops
        WHERE Title LIKE %s
    """
    # Pagination calculation
        count_query = f"SELECT COUNT(*) as total {query_base}"
        cursor.execute(count_query, (f"%{search_query}%",))
        total = cursor.fetchone()['total']
        total_pages = math.ceil(total / per_page)

    # Fetching paginated workshops
        workshops_query = f"""
    SELECT w.WorkshopID, w.Title, w.Details, w.Location, w.Date, w.Time, w.Cost, w.Capacity, t.UserId, t.FirstName, t.FamilyName
    FROM Workshops w
    INNER JOIN TutorProfiles t ON w.TutorID = t.UserID
    WHERE w.Title LIKE %s
    ORDER BY w.WorkshopID DESC
    LIMIT %s OFFSET %s;
"""

        offset = (page - 1) * per_page
        cursor.execute(workshops_query, (f"%{search_query}%", per_page, offset))
        workshops = cursor.fetchall()

        cursor.close()
        connection.close()
    # Filter off expired workshops
        current_date = date.today()
        print(current_date)
        return render_template('member/workshopList.html', workshops=workshops, page=page, total_pages=total_pages,current_date=current_date, format_date = format_date)


@app.route("/workshops/booking/<int:workshopID>", methods = ['POST','GET'])
@require_role(1) 
def workshop(workshopID):
  if request.method =='POST':
    #get workshop for render template
    cursor = getCursor()
    cursor.execute('SELECT w.WorkshopID, w.Details, w.Location, w.Date, w.Time, w.Cost, w.Capacity, t.UserID, t.FirstName, t.FamilyName FROM Workshops w INNER JOIN TutorProfiles t on w.TutorID = t.UserID WHERE WorkshopID = %s;',(workshopID,))

    workshop = cursor.fetchone()

    #get memberID 
    username = session.get('username')
    cursor = getCursor()
    cursor.execute("SELECT UserID FROM Users where Username = %s;",(username,))
    memberID = cursor.fetchone()
    print(memberID[0])
    #get Date
    cursor = getCursor()
    cursor.execute("SELECT * FROM Workshops WHERE WorkshopID = %s",(workshopID,))
    workshop_info = cursor.fetchone()
    date = workshop_info[4]
    capacity = workshop_info[7]
    print(date)
    print('***************')
    print(capacity)
    print('***************')
    #Transer the format of date
    workshop_date = format_date(date, format='%Y-%m-%d')
    # Check if already existed to avoid repetitive booking 
    connection = getDbConnection()
    cursor = connection.cursor()
    sql_check = """
                SELECT * FROM Bookings 
                WHERE MemberID = %s AND WorkshopID = %s AND BookingDate = %s;
 
        """
    cursor.execute(sql_check,(memberID[0], workshopID, date))
    booking_existed = cursor.fetchone()
    if not booking_existed:
    # check if there is vacancy to book
        sql = """
                SELECT count(*)
                FROM Bookings
                WHERE WorkshopID = %s;

             """
        cursor = getCursor()
        cursor.execute(sql,(workshopID,))
        already_booked =cursor.fetchone()[0]
        print(already_booked)
        if already_booked < capacity:
        # INSERT INTO Bookings  
            sql_insert = """
                INSERT INTO Bookings (MemberID, WorkshopID, BookingDate, CreatedAt)
                VALUES (%s, %s, %s, CURDATE());
                
            """
            cursor.execute(sql_insert,(memberID[0], workshopID, date))
            connection.commit()
            cursor.close()
            connection.close()
            flash('You have successfully booked this workshop!','success')
        else:
            flash('This workshop is already fully booked!','danger') 
    else:
        flash('You booked this workshop before!','danger')
  return render_template('/member/workshop_booking.html',workshop = workshop, format_date = format_date )
    
    




# profile that was missing
@app.route("/profile/member")
def member_profile():
    #get userID
    msg = ""
    username = session.get('username')
    cur = getCursor()
    cur.execute("SELECT * FROM Users where Username = %s;",(username,))
    user = cur.fetchone()
    # get proflie
    cur.execute("select * FROM MemberProfiles where UserID = %s;",(user[0],))
    profile = cur.fetchone()
    return render_template('member/member_profile.html', profile = profile, msg = msg)


# upload image
@app.route("/upload/image/<int:userID>", methods=['POST','GET'])
def upload_image(userID):
    msg=""
    if request.method == 'POST':
        if 'photo' not in request.files:
            msg = 'No file part in the request'
            return render_template('member/upload_image.html', msg=msg) 
        file = request.files['photo']
        if file.filename == '':
            msg = 'No selected file'
            return render_template('member/upload_image.html', msg=msg) 
        if file:
            # Save the uploaded file
            global dir_path
            img_folder = dir_path + "/static/images/members/"
            file.save(os.path.join(img_folder, file.filename))
            msg = 'File uploaded successfully'
            # Database action here
            cursor = getCursor()
            cursor.execute("UPDATE MemberProfiles SET ProfileImage = %s where UserId = %s",(file.filename, userID))

            cursor.execute("select * from MemberProfiles where UserId = %s",(userID,))
            profile = cursor.fetchone()
           
            return render_template('member/member_profile.html',profile = profile) 
    else:
     
        return render_template('member/upload_image.html', userID = userID) 
    

#jump to tutor profile through workshop list
@app.route("/profile/tutor/<int:userID>")
def check_tutor(userID):
    role = session.get('role')
    cur = getCursor()
    cur.execute("select * FROM TutorProfiles where UserID = %s;",(userID,))
    profile = cur.fetchone()
    return render_template('tutor/tutor_profile.html', profile = profile, role = role)

#read the reminder from manager and close it
@app.route("/reminder", methods=['POST','GET'])
def read_msg():
     #get userID
    username = session.get('username')
    cur = getCursor()
    cur.execute("SELECT * FROM Users where Username = %s;",(username,))
    user = cur.fetchone()
    cur.execute("SELECT * FROM MemberProfiles WHERE UserID = %s", (user[0], ))
    name = cur.fetchone()
    title = name[1]
    first_name = name[2]
    family_name = name[3]
    connection = getDbConnection()
    if request.method=='POST':
         cur = getCursor()
         sql = """
            UPDATE Subscriptions s SET Reminder = "No"
            WHERE MemberID = %s
            AND DATEDIFF(s.EndDate, CURDATE()) BETWEEN 0 AND 7
            AND Reminder = "Yes";
            """
         cur.execute(sql,(user[0],))
         connection.commit()
         return redirect(url_for('member_dashboard'))
    return render_template('member/reminder.html',title = title, first_name = first_name, family_name = family_name)