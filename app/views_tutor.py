from flask import Flask, flash, jsonify
from app import app
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import session
import os
import re
from app.config.database import getCursor, getDbConnection
from app.config.helpers import require_role, format_date
from app.config.models import get_all_locations, get_tutors_for_dropdown
from app.config.helpers import format_date

dir_path = os.path.dirname(os.path.realpath(__file__))

@app.route('/tutor')
def tutor_dashboard():
    if 'loggedin' in session and session['role'] == 2:
        return render_template('dashboard/tutor_dashboard.html', username=session['username'])
    return redirect(url_for('login'))
  
@app.route('/booking/lesson/details/<int:booking_id>',methods=['GET', 'POST'])
@require_role(2)
def lesson_booking_details(booking_id):
    conn = getDbConnection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        status = request.form.get('status')
        # Default to an empty string if note is not provided
        note = request.form.get('note', '')  
        
        try:
            cursor.execute("""
                UPDATE Bookings
                SET Status = %s, Note = %s
                WHERE BookingID = %s
            """, (status, note, booking_id))
            conn.commit()
            flash('Booking updated successfully.', 'success')
        except Exception as e:
            conn.rollback()
            flash('An error occurred while updating the booking.', 'danger')
            print(e)
        finally:
            cursor.close()
            conn.close()
        # Redirect to the same page to show the updated details
        return redirect(url_for('lesson_booking_details', booking_id=booking_id))
    
    cursor.execute("""
        SELECT 
            b.BookingID, 
            b.Status, 
            b.Note,
            l.Date, 
            l.StartTime, 
            l.EndTime, 
            l.Location, 
            l.Cost,
            l.IsBooked,
            lt.Name AS LessonType, 
            lt.Description,
            m.Title,
            m.FirstName, 
            m.FamilyName,
            m.PhoneNumber,
            m.Email,
            m.ProfileImage
        FROM Bookings b
        JOIN OneOnOneLessons l ON b.LessonID = l.LessonID
        JOIN LessonTypes lt ON l.LessonTypeID = lt.LessonTypeID
        JOIN MemberProfiles m ON b.MemberID = m.UserID
        WHERE b.BookingID = %s
    """, (booking_id,))
    
    booking_details = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not booking_details:
        flash('Booking not found.', 'danger')
        return redirect(url_for('tutor_dashboard'))  # Redirect to a default page if booking is not found
    
    return render_template('tutor/lesson_booking_details.html', booking=booking_details, format_date = format_date)

  
@app.route('/editTutor/<int:profileID>', methods=['POST','GET'])
@require_role(2)
def editTutor(profileID):
    msg=""
    if request.method == 'POST':
        if 'photo' not in request.files:
            msg = 'No file part in the request'
            return render_template('tutor/tutorProfileEdit.html', msg=msg) 
        file = request.files['photo']
        if file.filename == '':
            msg = 'No selected file'
            return render_template('tutor/tutorProfileEdit.html', msg=msg) 
        if file:
            # Save the uploaded file
            file.save(dir_path+'/static/images/tutors/' + file.filename)
            msg = 'File uploaded successfully'
            # Database action here
            cursor = getCursor()
            cursor.execute("update TutorProfiles set ProfileImage = %s where UserId = %s",(file.filename,profileID,))

            cursor.execute("select * from TutorProfiles where UserId = %s",(profileID,))
            tutor = cursor.fetchone()

            return render_template('tutor/tutorProfileEdit.html', msg=msg, profileID=profileID,tutor=tutor,) 
    else:
        cursor = getCursor()      
        cursor.execute("select * from TutorProfiles where UserId = %s",(profileID,))
        tutor = cursor.fetchone()
        msg = request.args.get('msg', "")
        return render_template('tutor/tutorProfileEdit.html', msg=msg, profileID=profileID, tutor=tutor,) 


@app.route('/tutor/lessons', methods=['GET', 'POST'])
def tutor_manage_lesson():
    if 'loggedin' in session and (session['role'] == 2 or session['role'] == 3):
        tutor_id = session['id']
        connection = getCursor()
        connection.execute(f"""
                           SELECT ool.LessonID,
                                lt.Name AS LessonName,
                                ool.Date,
                                ool.StartTime,
                                ool.EndTime,
                                ool.Location,
                                ool.Cost,
                                ool.IsBooked
                           FROM OneOnOneLessons ool
                           JOIN LessonTypes lt ON ool.LessonTypeID = lt.LessonTypeID
                           WHERE ool.TutorID = %s;
                           """, (tutor_id,))
        tutor_lessons = connection.fetchall()
        return render_template('tutor/tutor_manage_lesson.html', tutor_lessons=tutor_lessons, format_date = format_date)
    else:
        return redirect(url_for('login'))

@app.route('/edit/lesson/<int:lesson_id>', methods=['GET', 'POST'])
@require_role(2)
def tutor_edit_lesson(lesson_id):
    connection = getDbConnection()
    try:
        if request.method == 'POST':
            date = request.form['date']
            start_time = request.form['start_time']
            end_time = request.form['end_time']
            location = request.form['location'].strip()
            cost = request.form['cost']
            is_booked = request.form['is_booked']

            cursor = connection.cursor()
            sql = "UPDATE OneOnOneLessons SET Date = %s, StartTime = %s, EndTime = %s, Location = %s, Cost = %s, IsBooked = %s WHERE LessonID = %s"
            cursor.execute(sql, (date, start_time, end_time, location, cost, is_booked, lesson_id))
            connection.commit()
            flash('Lesson updated successfully!', 'success')
            if session.get('role') == 3:
                return redirect(url_for('view_lessons'))
            elif session.get('role') == 2:
                return redirect(url_for('tutor_manage_lesson'))
        else:
            cursor = connection.cursor(dictionary=True) 
            sql ="""SELECT ooo.LessonID, ooo.TutorID, ooo.Date, ooo.StartTime, ooo.EndTime, l.LocationName as Location, ooo.Cost, ooo.IsBooked, ooo.LessonTypeID, ooo.CreatedAt, l.Description, l.Available,  t.FirstName AS TutorFirstName, t.FamilyName AS TutorFamilyName, l.LocationID 
            FROM OneOnOneLessons ooo
            inner join Location l ON ooo.Location = l.LocationID
            inner join TutorProfiles t ON t.UserID = ooo.TutorID
            WHERE LessonID = %s """
            cursor.execute(sql, (lesson_id,))
            lesson = cursor.fetchone()
            locations = get_all_locations(1)
            if lesson:
                return render_template('tutor/tutor_edit_lesson.html', lesson=lesson, locations=locations)
            else:
                flash('Lesson not found.', 'danger')
                return redirect(url_for('tutor_manage_lesson'))
    except Exception as e:
        flash(f"Database error occurred: {e}", 'danger')
    finally:
        if connection:
            connection.close()
    # return redirect(url_for('index'))
           
   
@app.route('/delete_lesson/<int:lesson_id>', methods=['POST'])
@require_role(2)
def delete_lesson(lesson_id):
    connection = getDbConnection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM OneOnOneLessons WHERE LessonID = %s", (lesson_id,))
        connection.commit()
        flash('Lesson deleted successfully.', 'success')
    except Exception as e:
        # Log the error if needed
        flash('This lesson cannot be deleted as it is related to other bookings', 'danger')
    finally:
        cursor.close()
        connection.close()

    if session.get('role') == 2:
        return redirect(url_for('tutor_manage_lesson'))
    elif session.get('role') == 3:
        return redirect(url_for('view_lessons'))

@app.route('/tutor_add_lesson', methods=['GET', 'POST'])
@require_role(2)
def tutor_add_lesson():
    if request.method == 'POST':
        name = request.form['name'].strip()
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        location = request.form['location'].strip()
        cost = request.form['cost']
        is_booked = request.form['is_booked']

        try:
            connection = getDbConnection()
            with connection.cursor() as cursor:
                # Get the LessonTypeID for the given name
                cursor.execute("SELECT LessonTypeID FROM LessonTypes WHERE Name = %s", (name,))
                lesson_type_id = cursor.fetchone()
                if not lesson_type_id:
                    flash('Lesson type not found.', 'danger')
                    return redirect(url_for('tutor_add_lesson'))

                # Insert the lesson with the LessonTypeID
                sql = "INSERT INTO OneOnOneLessons (LessonTypeID, TutorID, Date, StartTime, EndTime, Location, Cost, IsBooked) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(sql, (lesson_type_id[0], session['id'], date, start_time, end_time, location, cost, is_booked))
                connection.commit()
                flash('Lesson added successfully!', 'success')
        except Exception as e:
            connection.rollback()
            flash(f"Database error occurred: {e}", 'danger')
        finally:
            if connection:
                connection.close()

        return redirect(url_for('tutor_manage_lesson'))

    return render_template('tutor/tutor_add_lesson.html')


#profile
@app.route("/profile/tutor")
def tutor_profile():
    role = session.get('role')
    print(role)
    #get userID
    msg = ""
    username = session.get('username')
    cur = getCursor()
    cur.execute("SELECT * FROM Users where Username = %s;",(username,))
    user = cur.fetchone()
    # get proflie
    cur.execute("select * FROM TutorProfiles where UserID = %s;",(user[0],))
    profile = cur.fetchone()
    return render_template('tutor/tutor_profile.html', profile = profile, msg = msg, role=role)


#update info for tutor

@app.route('/update/info/tutor/<int:tutorID>' , methods=['GET', 'POST'])
def update_info_tutor(tutorID):
    msg = ""
    cur = getCursor()
    cur.execute("SELECT * FROM Users where UserID = %s;",(tutorID,))
    user = cur.fetchone()
    cur = getCursor()
    cur.execute("SELECT * FROM TutorProfiles where UserID = %s;",(user[0],))
    tutor = cur.fetchone()
    if request.method =='POST':
        title = request.form.get('title')
        first_name = request.form.get('firstname')
        family_name = request.form.get('familyname')
        position = request.form.get('position')
        phone = request.form.get('phonenumber')
        email = request.form.get('email')
        profile = request.form.get('profile')
        # using session to get username for define where in sql
        username = session.get('username')
        #validation for name
        pattern = re.compile("^[A-Za-z]+$")
        print(user[0])
        if pattern.match(first_name) and pattern.match(family_name):
        #update into Users table   
            cur.execute("UPDATE TutorProfiles SET Title = %s, FirstName = %s,FamilyName = %s, Position = %s, PhoneNumber = %s, Email = %s, TutorProfile = %s WHERE UserID = %s", (title, first_name, family_name, position, phone, email, profile, user[0]))
            
            flash('Information Updated','succes')
            return redirect(url_for('update_info_tutor', tutorID=tutorID))
        else:
            flash('Please make sure your inputs for names are only letters','danger')
            return render_template('updateinfo.html', msg=msg,  tutor=tutor, form_action = '/update/info/tutor')
        
    else:
        return render_template('updateinfo.html', msg=msg, tutor=tutor, form_action = '/update/info/tutor')
#  upload imgage
@app.route("/tutor/image/<int:userID>", methods=['POST','GET'])
def tutor_image(userID):
    msg=""
    if request.method == 'POST':
        if 'photo' not in request.files:
            msg = 'No file part in the request'
            return render_template('tutor/upload_image.html', msg=msg) 
        file = request.files['photo']
        if file.filename == '':
            msg = 'No selected file'
            return render_template('tutor/upload_image.html', msg=msg) 
        if file:
            # Save the uploaded file
            global dir_path
            img_folder = dir_path + "/static/images/tutors/"
            file.save(os.path.join(img_folder, file.filename))
            msg = 'File uploaded successfully'
            # Database action here
            cursor = getCursor()
            cursor.execute("UPDATE TutorProfiles SET ProfileImage = %s where UserId = %s",(file.filename, userID))

            cursor.execute("select * from TutorProfiles where UserId = %s",(userID,))
            profile = cursor.fetchone()
           
            return render_template('tutor/tutor_profile.html',profile = profile,role = 2) 
    else:
     
        return render_template('tutor/upload_image.html', userID = userID)
    
@app.route('/attendance')
@require_role(2)
def manage_attendance():
    tutors = get_tutors_for_dropdown() 
    return render_template('tutor/attendance.html', tutors=tutors)

@app.route('/get_participants/<session_type>/<int:session_id>')
@require_role(2)
def get_participants(session_type, session_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        if session_type == 'lesson':
            query = """
                SELECT m.UserID, m.FirstName, m.FamilyName, m.Email, a.Attended
                FROM Bookings b
                JOIN MemberProfiles m ON b.MemberID = m.UserID
                LEFT JOIN Attendance a ON a.BookingID = b.BookingID AND a.OneOnOneLessonID = %s
                WHERE b.LessonID = %s
            """
        else:  # workshop
            query = """
                SELECT m.UserID, m.FirstName, m.FamilyName, m.Email, a.Attended
                FROM Bookings b
                JOIN MemberProfiles m ON b.MemberID = m.UserID
                LEFT JOIN Attendance a ON a.BookingID = b.BookingID AND a.WorkshopID = %s
                WHERE b.WorkshopID = %s
            """
        cursor.execute(query, (session_id,session_id))
        participants = cursor.fetchall()
        return jsonify(participants)
    except Exception as e:
        print(e)
        return jsonify([]), 500
    finally:
        cursor.close()
        connection.close()


@app.route('/get_sessions/<session_type>/<int:tutor_id>', methods=['GET'])
@require_role(2)
def get_sessions(session_type, tutor_id):
    
    user_role = session.get('role')
    if not tutor_id and user_role == 3:
        flash('Please select a tutor.', 'warning')
        return redirect(url_for('manage_attendance'))

    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    if session_type == 'lesson':
        cursor.execute("""
        SELECT l.LessonID as id, CONCAT('Lesson: ', lt.Name) as name
        FROM OneOnOneLessons l
        JOIN LessonTypes lt ON l.LessonTypeID = lt.LessonTypeID
        WHERE l.TutorID = %s AND l.IsBooked = TRUE
    """, (tutor_id,))
    else:
        cursor.execute("""
        SELECT WorkshopID as id, CONCAT('Workshop: ', Title) as name
        FROM Workshops
        WHERE TutorID = %s
    """, (tutor_id,))
    sessions = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(sessions)

@app.route('/record_attendance', methods=['POST'])
@require_role(2)
def record_attendance():
    session_type = request.form['sessionType']
    session_id = request.form['session']
    
    if not session_type or not session_id:
        flash('Session type and session ID are required fields.', 'error')
        return redirect(url_for('manage_attendance'))  

    
    attended_member_ids = set(int(mid) for mid in request.form.getlist('attended[]'))
    connection = getDbConnection()
    cursor = connection.cursor()
    
    try:
        field_name = "OneOnOneLessonID" if session_type == 'lesson' else "WorkshopID"
        if session_type == 'lesson':
            query = """
                SELECT m.UserID, b.BookingID
                FROM Bookings b
                JOIN MemberProfiles m ON b.MemberID = m.UserID
                WHERE b.LessonID = %s
            """
        else:  # workshop
            query = """
                SELECT m.UserID, b.BookingID
                FROM Bookings b
                JOIN MemberProfiles m ON b.MemberID = m.UserID
                WHERE b.WorkshopID = %s
            """
        cursor.execute(query, (session_id,))
        bookings = cursor.fetchall()
        
        for MemberID, BookingID in bookings:
            attended = MemberID in attended_member_ids
            cursor.execute(f"""
                INSERT INTO Attendance (BookingID, MemberID, {field_name}, Attended, SessionType, Date)
                VALUES (%s, %s, %s, %s,%s, NOW())
                ON DUPLICATE KEY UPDATE Attended = %s
            """, (BookingID, MemberID, session_id, attended,session_type, attended))

        connection.commit()
        flash('Attendance recorded successfully!', 'success')
    except Exception as e:
        print(e)
        connection.rollback()
        flash('Failed to record attendance.', 'error')
    finally:
        cursor.close()
        connection.close()

    if session['role'] == 3:
         return redirect(url_for('manager_dashboard'))
    elif session['role'] == 2:
        return redirect(url_for('tutor_dashboard'))
   


@app.route('/view_attendance/<session_type>/<int:session_id>')
@require_role(2)
def view_attendance(session_type, session_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    # Fetch session name
    if session_type == 'lesson':
        cursor.execute("""
            SELECT Name AS SessionName FROM LessonTypes
            JOIN OneOnOneLessons ON LessonTypes.LessonTypeID = OneOnOneLessons.LessonTypeID
            WHERE OneOnOneLessons.LessonID = %s
        """, (session_id,))
    elif session_type == 'workshop':
        cursor.execute("""
            SELECT Title AS SessionName FROM Workshops
            WHERE WorkshopID = %s
        """, (session_id,))
    session = cursor.fetchone()
    session_name = session['SessionName'] if session else 'Session not found'

    # Fetch attendance records or all participants if no records exist
    query = """
        SELECT MemberProfiles.FirstName, MemberProfiles.FamilyName, MemberProfiles.Email, Attendance.Date, Attendance.Attended
        FROM Bookings
        JOIN MemberProfiles ON Bookings.MemberID = MemberProfiles.UserID
        LEFT JOIN Attendance ON Bookings.BookingID = Attendance.BookingID AND Attendance.{}ID = %s
        WHERE Bookings.{}ID = %s
    """.format('OneOnOneLesson' if session_type == 'lesson' else 'Workshop', 'Lesson' if session_type == 'lesson' else 'Workshop')
    cursor.execute(query, (session_id, session_id))
    records = cursor.fetchall()

    cursor.close()
    connection.close()

    # If no records are fetched, set a default status
    if not records or all(record['Attended'] is None for record in records):
        for record in records:
            record['Date'] = 'Not yet recorded'
            record['Attended'] = 'Not Yet Recorded'

    return render_template('tutor/view_attendance.html', records=records, session_name=session_name, session_type=session_type)

@app.route('/tutor/lesson_bookings')
@require_role(2)
def lesson_bookings():
    tutor_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT l.LessonID, lt.Name as LessonType, l.Date, l.StartTime, l.EndTime, m.FirstName, m.FamilyName, b.BookingID, b.Status
            FROM OneOnOneLessons l
            JOIN LessonTypes lt ON l.LessonTypeID = lt.LessonTypeID
            JOIN Bookings b ON l.LessonID = b.LessonID
            JOIN MemberProfiles m ON b.MemberID = m.UserID
            WHERE l.TutorID = %s AND b.Status IN ('Confirmed', 'Cancelled')
            ORDER BY l.Date DESC, l.StartTime
        """, (tutor_id,))
        bookings = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template('tutor/lesson_booking.html', bookings=bookings, format_date = format_date)

@app.route('/tutor/workshop')
@require_role(2) 
def tutor_workshop():
    tutor_id = session.get('id')
    if not tutor_id:
        flash('User not logged in.', 'error')
        return redirect(url_for('login'))

    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT w.WorkshopID, w.Title, w.Date, w.Time, l.LocationName, w.Cost
            FROM Workshops w
            LEFT JOIN Location l ON w.Location = l.LocationID  # Assuming 'Location' in Workshops refers to LocationID
            WHERE w.TutorID = %s
            ORDER BY w.Date DESC, w.Time DESC
        """, (tutor_id,))
        workshops = cursor.fetchall()
    except Exception as e:
        flash(f'Error fetching workshops: {e}', 'error')
        workshops = []
    finally:
        cursor.close()
        connection.close()

    return render_template('tutor/tutor_workshop.html', workshops=workshops)
