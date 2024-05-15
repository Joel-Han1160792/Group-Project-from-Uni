from aifc import Error
import functools
import math
from app import app
from flask import jsonify, redirect, render_template, url_for, flash
from flask import request
from flask import session
import re
from app.config.database import getCursor, getDbConnection
from app.config.helpers import require_role
from app.config.models import get_tutors_for_dropdown, get_all_locations
from datetime import datetime
from app.config.helpers import format_date


@app.route('/manager')
def manager_dashboard():
    if 'loggedin' in session and session['role'] == 3:
        return render_template('dashboard/manager_dashboard.html', username=session['username'])
    return redirect(url_for('login'))

#update info for manager
@app.route('/update/info/manager' , methods=['GET', 'POST'])
def update_info_manager():
    msg = ""
    username = session.get('username')
    cur = getCursor()
    cur.execute("SELECT * FROM Users where Username = %s;",(username,))
    user = cur.fetchone()
    cur = getCursor()
    cur.execute("SELECT * FROM ManagerProfiles where UserID = %s;",(user[0],))
    manager = cur.fetchone()
    if request.method =='POST':
        title = request.form.get('title')
        first_name = request.form.get('firstname')
        family_name = request.form.get('familyname')
        position = request.form.get('position')
        phone = request.form.get('phonenumber')
        email = request.form.get('email')
        # using session to get username for define where in sql

        username = session.get('username')
        #validation for name
        pattern = re.compile("^[A-Za-z]+$")
        if pattern.match(first_name) and pattern.match(family_name):
        #update into Users table   
           
            cur.execute("UPDATE ManagerProfiles SET Title = %s, FirstName = %s,FamilyName = %s, Position = %s, PhoneNumber = %s, Email = %s WHERE UserID = %s", (title, first_name, family_name, position, phone, email, user[0]))
            flash('Information Updated','succes')
            return redirect(url_for('update_info_manager'))
        else:
            flash('Please make sure your inputs for names are only letters','danger')
            return render_template('updateinfo.html', msg=msg, manager=manager, form_action = '/update/info/manager')

    else:
        return render_template('updateinfo.html', msg=msg, manager=manager, form_action = '/update/info/manager')


@app.route('/workshop/new', methods=['GET', 'POST'])
@require_role(3)
def add_workshop():
    if request.method == 'POST':
        title = request.form['title']
        details = request.form['details']
        location = request.form['location']
        date = request.form['date']
        time = request.form['time']
        cost = request.form['cost']
        capacity = request.form['capacity']
        tutor_id = request.form['tutor_id']

        if not title or not details or not location:
            flash('Please fill out all required fields.', 'danger')
        elif not re.match(r'^\d+(\.\d{1,2})?$', cost):
            flash('Invalid cost format. Please enter a numeric value.', 'danger')
        elif not capacity.isdigit() or int(capacity) <= 0:
            flash('Capacity must be a positive integer.', 'danger')
        else:
            connection = getDbConnection()
            cursor = connection.cursor()
            insert_query = """
            INSERT INTO Workshops (Title, Details, Location, Date, Time, Cost, Capacity, TutorID)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (title, details, location, date, time, cost, capacity, tutor_id))
            connection.commit()
            cursor.close()
            connection.close()            
            flash('Workshop added successfully.', 'success')
            return redirect(url_for('view_workshops')) 

    tutors = get_tutors_for_dropdown() 
    locations = get_all_locations(1) 
    return render_template('manager/create_workshop.html', tutors=tutors, locations=locations)

@app.route('/workshops/edit/<int:workshop_id>', methods=['GET', 'POST'])
@require_role(2)
def edit_workshop(workshop_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    # Fetch workshop details for GET request
    if request.method == 'GET':
        cursor.execute("SELECT WorkshopID, Title, Details, l.locationName as Location, Date, Time,Cost,Capacity,TutorID,CreatedAt,l.locationID FROM Workshops w inner join Location l on l.locationID= w.Location WHERE WorkshopID = %s", (workshop_id,))
        workshop = cursor.fetchone()
        if workshop:
            tutors = get_tutors_for_dropdown() 
            locations = get_all_locations(1) 
            return render_template('manager/edit_workshop.html', workshop=workshop, tutors=tutors, locations= locations)
        else:
            flash('Workshop not found.', 'danger')
            return redirect(url_for('view_workshops')) 
        
    # Handle POST request for updating workshop details
    if request.method == 'POST':
        title = request.form['title']
        details = request.form['details']
        location = request.form['location']
        date = request.form['date']
        time = request.form['time']
        cost = request.form['cost']
        capacity = request.form['capacity']
        tutor_id = request.form['tutor_id']


        if not title or not details or not location:
            flash('Please fill out all required fields.', 'danger')
        elif not re.match(r'^\d+(\.\d{1,2})?$', cost):
            flash('Invalid cost format. Please enter a numeric value.', 'danger')
        elif not capacity.isdigit() or int(capacity) <= 0:
            flash('Capacity must be a positive integer.', 'danger')
        else:
            update_query = """
            UPDATE Workshops
            SET Title = %s, Details = %s, Location = %s, Date = %s, Time = %s, Cost = %s, Capacity = %s, TutorID = %s
            WHERE WorkshopID = %s
            """
            cursor.execute(update_query, (title, details, location, date, time, cost, capacity, tutor_id, workshop_id))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Workshop updated successfully.', 'success')
            return redirect(url_for('view_workshops')) 
    
    return render_template('manager/edit_workshop.html')

@app.route('/workshops', methods=['GET'])
def view_workshops():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Set the number of items per page

    query_base = """
        FROM Workshops as w
        Inner join Location l on l.LocationID = w.Location
        WHERE Title LIKE %s
    """
    # Pagination calculation
    count_query = f"SELECT COUNT(*) as total {query_base}"
    cursor.execute(count_query, (f"%{search_query}%",))
    total = cursor.fetchone()['total']
    total_pages = math.ceil(total / per_page)

    # Fetching paginated workshops
    workshops_query = f"""
        SELECT WorkshopID, Title, Details, l.LocationName as Location, Date, Time, Cost, Capacity, TutorID, l.LocationID
        {query_base}    
        ORDER BY WorkshopID DESC
        LIMIT %s OFFSET %s
    """
    offset = (page - 1) * per_page
    cursor.execute(workshops_query, (f"%{search_query}%", per_page, offset))
    workshops = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('manager/view_workshop.html', workshops=workshops, page=page, total_pages=total_pages,  format_date = format_date)



@app.route('/location/new', methods=['GET', 'POST'])
@require_role(3)
def add_location():
    if request.method == 'POST':
        locationName = request.form['locationName']
        description = request.form['description']
        available = request.form['available']
        locationID = request.form['locationID']
        
        
        if not locationName or not description or not available:
            flash('Please fill out all required fields.', 'danger')

        
        else:
            connection = getDbConnection()
            cursor = connection.cursor()
            cursor.execute("select count(1) from Location l where l.LocationName=%s", (locationName, ))
            existLoc= cursor.fetchone()
       
           
            if existLoc[0] > 0:
                flash('Location is existed, please change to other location name.', 'danger')
            else:
                available = int(request.form['available'])
                insert_query = """
                INSERT INTO Location ( LocationName, Description, Available)
                VALUES ( %s, %s, %s)
                """
                cursor.execute(insert_query, ( locationName, description, available))
                connection.commit()
                cursor.close()
                connection.close()            
                flash('Location added successfully.', 'success')
                return redirect(url_for('location_management')) 

    tutors = get_tutors_for_dropdown() 
    locations = get_all_locations(0) 
    return render_template('manager/add_location.html', tutors=tutors, locations=locations)



@app.route('/location/edit/<string:locationID>', methods=['GET', 'POST'])
@require_role(3)
def edit_location(locationID):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    # Fetch workshop details for GET request
    if request.method == 'GET':
        cursor.execute("SELECT * FROM Location WHERE locationID = %s", (locationID,))
        location = cursor.fetchone()
        print(location)
        if location:
           
            return render_template('manager/edit_location.html', location= location)
        else:
            flash('Location not found.', 'danger')
            return redirect(url_for('location_management')) 
        
    # Handle POST request for updating workshop details
    if request.method == 'POST':
        locationName = request.form['locationName']
        description = request.form['description']
        available = int(request.form['available'])
        locationID = request.form['locationID']
        if not locationName :
            flash('Please fill out all required fields.', 'danger')
        else:
            update_query = """
            UPDATE Location
            SET LocationName = %s, Description = %s, Available = %s
            WHERE LocationID = %s
            """
            cursor.execute(update_query, (locationName, description, available, locationID))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Location updated successfully.', 'success')
            return redirect(url_for('location_management')) 
    
    return render_template('manager/edit_location.html')

@app.route('/delete_location/<string:locationID>', methods=['POST'])
@require_role(3)
def delete_location(locationID):
    connection = getDbConnection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM Location WHERE locationID = %s", (locationID,))
        connection.commit()
        flash('Location deleted successfully.', 'success')
    except Exception as e:
        # Log the error if needed
        flash('An error occurred while deleting the location.', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('location_management'))

@app.route('/location-management', methods=['GET'])
@require_role(3)
def location_management():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Set the number of items per page

    query_base = """
        FROM Location
        WHERE LocationName LIKE %s
    """
    # Pagination calculation
    count_query = f"SELECT COUNT(*) as total {query_base}"
    cursor.execute(count_query, (f"%{search_query}%",))
    total = cursor.fetchone()['total']
    total_pages = math.ceil(total / per_page)

    # Fetching paginated workshops
    locations_query = f"""
        SELECT LocationName, Description, Available, LocationID
        {query_base}
        ORDER BY LocationName
        LIMIT %s OFFSET %s
    """
    offset = (page - 1) * per_page
    cursor.execute(locations_query, (f"%{search_query}%", per_page, offset))

    locations = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('manager/view_locations.html',locations= locations, page=page, total_pages=total_pages)

@app.route('/lesson-schedules', methods=['GET'])
@require_role(3)
def view_lessons():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Set the number of items per page

    query_base = """
        FROM OneOnOneLessons l
        JOIN LessonTypes lt ON l.LessonTypeID = lt.LessonTypeID
        JOIN TutorProfiles t ON l.TutorID = t.UserID
        Inner join Location as loc on loc.LocationID = l.Location
        WHERE lt.Name LIKE %s
    """
    # Pagination calculation
    count_query = f"SELECT COUNT(*) as total {query_base}"
    cursor.execute(count_query, (f"%{search_query}%",))
    total = cursor.fetchone()['total']
    total_pages = math.ceil(total / per_page)

    # Fetching paginated workshops
    lessons_query = f"""
        SELECT l.LessonID, l.*, lt.Name AS LessonType, lt.Description,
            t.FirstName AS TutorFirstName, t.FamilyName AS TutorFamilyName,
            t.ProfileImage AS TutorProfileImage, loc.LocationName
        {query_base}
        ORDER BY l.Date ASC
        LIMIT %s OFFSET %s
    """
    offset = (page - 1) * per_page
    cursor.execute(lessons_query, (f"%{search_query}%", per_page, offset))
    lessons = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('manager/view_lessons.html', lessons=lessons, page=page, total_pages=total_pages,  format_date = format_date)


@app.route('/manager/edit/lesson/<int:lesson_id>', methods=['GET', 'POST'])
@require_role(3)
def manager_edit_lesson(lesson_id):
    connection = getDbConnection()
    try:
        if request.method == 'POST':
            date = request.form['date']
            start_time = request.form['start_time']
            end_time = request.form['end_time']
            location = request.form['location'].strip()
            cost = request.form['cost']
            is_booked = request.form['is_booked']
            lesson_type_id = request.form['lesson_type']
            tutor_id = request.form['tutor']

            cursor = connection.cursor()
            sql = "UPDATE OneOnOneLessons SET Date = %s, StartTime = %s, EndTime = %s, Location = %s, Cost = %s, IsBooked = %s, LessonTypeID = %s, TutorID = %s WHERE LessonID = %s"
            cursor.execute(sql, (date, start_time, end_time, location, cost, is_booked, lesson_type_id, tutor_id, lesson_id))
            connection.commit()
            flash('Lesson updated successfully!', 'success')
            return redirect(url_for('view_lessons'))
        else:
            cursor = connection.cursor(dictionary=True) 
            sql = """SELECT ooo.LessonID, ooo.TutorID, ooo.Date, ooo.StartTime, ooo.EndTime, l.LocationName as Location, ooo.Cost, ooo.IsBooked, ooo.LessonTypeID, ooo.CreatedAt, l.Description, l.Available,  t.FirstName AS TutorFirstName, t.FamilyName AS TutorFamilyName, l.LocationID 
            FROM OneOnOneLessons ooo
            INNER JOIN Location l ON ooo.Location = l.LocationID
            INNER JOIN TutorProfiles t ON t.UserID = ooo.TutorID
            WHERE LessonID = %s """
            cursor.execute(sql, (lesson_id,))
            lesson = cursor.fetchone()

            # Fetching lesson types
            lesson_types_query = "SELECT LessonTypeID, Name FROM LessonTypes"
            cursor.execute(lesson_types_query)
            lesson_types = cursor.fetchall()

            # Fetching tutor names
            tutors_query = "SELECT UserID, CONCAT(FirstName, ' ', FamilyName) AS TutorName FROM TutorProfiles"
            cursor.execute(tutors_query)
            tutors = cursor.fetchall()

            locations = get_all_locations(1)
            if lesson:
                return render_template('manager/manager_edit_lesson.html', lesson=lesson, lesson_types=lesson_types, tutors=tutors, locations=locations)
            else:
                flash('Lesson not found.', 'danger')
                return redirect(url_for('view_lessons'))
    except Exception as e:
        flash(f"Database error occurred: {e}", 'danger')
    finally:
        if connection:
            connection.close()



@app.route('/manager/add/lesson', methods=['GET', 'POST'])
@require_role(3)
def manager_add_lesson():
    try:
        connection = getDbConnection()
        with connection.cursor() as cursor:
            if request.method == 'POST':
                lesson_type_id = request.form['lesson_type']
                date = request.form['date']
                start_time = request.form['start_time']
                end_time = request.form['end_time']
                location_id = request.form['location']
                tutor_id = request.form['tutor']
                cost = request.form['cost']
                is_booked = request.form['is_booked']

                sql = "INSERT INTO OneOnOneLessons (LessonTypeID, TutorID, Date, StartTime, EndTime, Location, Cost, IsBooked) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(sql, (lesson_type_id, tutor_id, date, start_time, end_time, location_id, cost, is_booked))
                connection.commit()
                flash('Lesson added successfully!', 'success')
                return redirect(url_for('view_lessons'))
            else:
                # Fetch lesson types
                cursor.execute("SELECT LessonTypeID, Name FROM LessonTypes")
                lesson_types = cursor.fetchall()

                # Fetch tutors
                cursor.execute("SELECT UserID, CONCAT(FirstName, ' ', FamilyName) AS TutorName FROM TutorProfiles")
                tutors = cursor.fetchall()

                # Fetch locations
                cursor.execute("SELECT LocationID, LocationName FROM Location")
                locations = cursor.fetchall()

                return render_template('manager/manager_add_lesson.html', lesson_types=lesson_types, tutors=tutors, locations=locations)
    except Exception as e:
        flash(f"Database error occurred: {e}", 'danger')
    finally:
        if connection:
            connection.close()

    return redirect(url_for('view_lessons'))



@app.route('/delete_workshop/<int:workshop_id>', methods=['POST'])
@require_role(3)
def delete_workshop(workshop_id):
    connection = getDbConnection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM Workshops WHERE WorkshopID = %s", (workshop_id,))
        connection.commit()
        flash('Workshop deleted successfully.', 'success')
    except Exception as e:
        # Log the error if needed
        flash('An error occurred while deleting the workshop.', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('view_workshops'))

@app.route('/create/lessonType', methods=['GET', 'POST'])
@require_role(3)
def add_lesson_type():
    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form['description'].strip()

        if not name or not description:
            flash('All fields are required.', 'danger')
            return redirect(url_for('add_lesson_type'))
        try:
            connection = getDbConnection()
            with connection.cursor() as cursor:
                # Prepare SQL query
                sql = "INSERT INTO LessonTypes (Name, Description) VALUES (%s, %s)"
                # Execute the query
                cursor.execute(sql, (name, description))
                # Commit the transaction
                connection.commit()
                flash('Lesson type added successfully!', 'success')
        except Exception as e:
            # Rollback in case of error
            connection.rollback()
            flash(f"Database error occurred: {e}", 'danger')
        finally:
            if connection:
                connection.close()

        return redirect(url_for('list_lesson_types'))
    
    return render_template('manager/create_lesson_type.html')

@app.route('/edit/lessonType/<int:lesson_type_id>', methods=['GET', 'POST'])
@require_role(3)
def edit_lesson_type(lesson_type_id):
    connection = getDbConnection()
    try:
        if request.method == 'POST':
            name = request.form['name'].strip()
            description = request.form['description'].strip()

            if not name or not description:
                flash('All fields are required.', 'danger')
                return redirect(url_for('edit_lesson_type', lesson_type_id=lesson_type_id))

            with connection.cursor() as cursor:
                sql = "UPDATE LessonTypes SET Name = %s, Description = %s WHERE LessonTypeID = %s"
                cursor.execute(sql, (name, description, lesson_type_id))
                connection.commit()
                flash('Lesson type updated successfully!', 'success')
                return redirect(url_for('list_lesson_types'))
        else:
            with connection.cursor(dictionary=True) as cursor:
                sql = "SELECT LessonTypeID, Name, Description FROM LessonTypes WHERE LessonTypeID = %s"
                cursor.execute(sql, (lesson_type_id,))
                lesson_type = cursor.fetchone()
                if lesson_type:
                    return render_template('manager/edit_lesson_type.html', lesson_type=lesson_type)
                else:
                    flash('Lesson type not found.', 'danger')
                    return redirect(url_for('list_lesson_types'))          
    except Exception as e:
        flash(f"Database error occurred: {e}", 'danger')
    finally:
        if connection:
            connection.close()

@app.route('/lesson_types', methods=['GET'])
@require_role(3)
def list_lesson_types():
    search_query = request.args.get('search', '')
    connection = getDbConnection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            if search_query:
                sql = "SELECT * FROM LessonTypes WHERE Name LIKE %s ORDER BY Name DESC"
                cursor.execute(sql, ('%' + search_query + '%',))
            else:
                sql = "SELECT * FROM LessonTypes ORDER BY Name DESC"
                cursor.execute(sql)
            lesson_types = cursor.fetchall()
    except Exception as e:
        flash(f"Database error occurred: {e}", 'danger')
    finally:
        if connection:
            connection.close()

    return render_template('manager/view_lesson_type.html', lesson_types=lesson_types, search_query=search_query)

@app.route('/delete/lesson_type/<int:lesson_type_id>', methods=['POST'])
@require_role(3)
def delete_lesson_type(lesson_type_id):
    connection = getDbConnection()
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM LessonTypes WHERE LessonTypeID = %s"
            cursor.execute(sql, (lesson_type_id,))
            connection.commit()
            flash('Lesson type deleted successfully.', 'success')
    except Exception as e:
        flash(f"Database error occurred: {e}", 'danger')
        connection.rollback()
    finally:
        if connection:
            connection.close()

    return redirect(url_for('list_lesson_types'))

# profile that was missing
@app.route("/profile/manager")
@require_role(3)
def manager_profile():
    #get userID
    username = session.get('username')
    cur = getCursor()
    cur.execute("SELECT * FROM Users where Username = %s;",(username,))
    user = cur.fetchone()
    # get proflie
    cur.execute("select * FROM ManagerProfiles where UserID = %s;",(user[0],))
    profile = cur.fetchone()
    return render_template('manager/manager_profile.html', profile = profile)

@app.route("/member_subscription")
@require_role(3)
def member_subscription():
    connection = getCursor()

    # Get the search query from the URL parameters
    search_query = request.args.get('search', '')

    # Modify the SQL query to include the search condition
    sql_query = f"""
        SELECT
            m.UserID AS 'User ID/Member ID',
            CONCAT(m.FirstName, ' ', m.FamilyName) AS 'Member Name',
            s.Type AS 'Type from Subscription',
            s.StartDate AS 'Start Date',
            s.EndDate AS 'End Date',
            s.subscriptionStatus AS 'Subscription Status'
        FROM
            MemberProfiles m
        JOIN
            Subscriptions s ON m.UserID = s.MemberID
        WHERE
            CONCAT(m.FirstName, ' ', m.FamilyName) LIKE %s
    """

    # Execute the query with the search condition
    connection.execute(sql_query, (f"%{search_query}%",))
    member_subscriptions = connection.fetchall()

    return render_template("manager/member_subscription.html", member_subscriptions=member_subscriptions, search_query=search_query, format_date = format_date)


@app.route("/track_payment")
@require_role(3)
def track_payment():
    connection = getCursor()

    # Get the search query and type filter from the URL parameters
    search_query = request.args.get('search', '')
    type_filter = request.args.get('type', '')

    # Modify the SQL query to include the search condition and type filter
    sql_query = """
        SELECT 
            p.PaymentID,
            CONCAT(mp.FirstName, ' ', mp.FamilyName) AS MemberName,
            p.Amount,
            p.Date,
            p.Type
        FROM 
            Payments p
        INNER JOIN 
            MemberProfiles mp ON p.MemberID = mp.UserID
        WHERE 
            CONCAT(mp.FirstName, ' ', mp.FamilyName) LIKE %s
            AND (p.Type = %s OR %s = '')
        ORDER BY 
            p.PaymentID
    """

    # Execute the query with the search condition and type filter
    connection.execute(sql_query, (f"%{search_query}%", type_filter, type_filter))
    payments = connection.fetchall()

    return render_template("manager/track_payment.html", payments=payments, search_query=search_query, type_filter=type_filter,  format_date = format_date)



@app.route('/payment/<int:payment_id>')
def payment_detail(payment_id):
    connection = getDbConnection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Payments WHERE PaymentID = %s", (payment_id,))
            payment = cursor.fetchone()

            if payment is None:
                flash("Payment not found", 'danger')
                return redirect(url_for('view_payments'))

            payment_dict = {
                'PaymentID': payment[0],
                'Type': payment[7],
                'Amount': payment[4],
                'Date': payment[5],
            }

            if payment_dict['Type'] == 'Subscription':
                cursor.execute("SELECT Type, StartDate, EndDate, subscriptionStatus FROM Subscriptions WHERE SubscriptionID = %s", (payment[2],))
                subscription = cursor.fetchone()
                subscription_dict = {
                    'SubscriptionType': subscription[0],
                    'StartDate': subscription[1],
                    'EndDate': subscription[2],
                    'SubscriptionStatus': subscription[3]
                }
                payment_dict.update(subscription_dict)

            elif payment_dict['Type'] == 'Workshop' or payment_dict['Type'] == 'Lesson':
                cursor.execute("SELECT BookingID FROM Payments WHERE PaymentID = %s", (payment_id,))
                booking_id = cursor.fetchone()[0]

                if payment_dict['Type'] == 'Workshop':
                    cursor.execute("SELECT WorkshopID FROM Bookings WHERE BookingID = %s", (booking_id,))
                    workshop_id = cursor.fetchone()[0]
                    cursor.execute("SELECT Title, Location, Date, Time FROM Workshops WHERE WorkshopID = %s", (workshop_id,))
                    workshop = cursor.fetchone()
                    workshop_dict = {
                        'WorkshopTitle': workshop[0],
                        'Location': workshop[1],
                        'Date': workshop[2],
                        'Time': workshop[3]
                    }
                    payment_dict.update(workshop_dict)

                elif payment_dict['Type'] == 'Lesson':
                    cursor.execute("SELECT BookingID FROM Payments WHERE PaymentID = %s", (payment_id,))
                    booking_id = cursor.fetchone()[0]
                    cursor.execute("SELECT LessonID FROM Bookings WHERE BookingID = %s", (booking_id,))
                    lesson_id = cursor.fetchone()[0]
                    cursor.execute("SELECT LessonTypeID, Date, StartTime, EndTime, Location FROM OneOnOneLessons WHERE LessonID = %s", (lesson_id,))
                    lesson = cursor.fetchone()
                    lesson_type_id = lesson[0]
                    lesson_date = lesson[1]
                    lesson_starttime = lesson[2]
                    lesson_endtime = lesson[3]
                    lesson_location = lesson[4]
                
                    cursor.execute("SELECT Name FROM LessonTypes WHERE LessonTypeID = %s", (lesson_type_id,))
                    lesson_name = cursor.fetchone()[0]
                    lesson_dict = {
                    'LessonType': lesson_name,
                    'Date': lesson_date,
                    'StartTime': lesson_starttime,
                    'EndTime': lesson_endtime,
                    'Location': lesson_location
                    }
                    payment_dict.update(lesson_dict)



    except Exception as e:
        flash(f"Database error occurred: {e}", 'danger')
    finally:
        connection.close()

    return render_template('manager/payment_detail.html', payment=payment_dict)





# get subscriptions closed to enddate
def get_subs_endsoon():
        cur = getCursor()
        sql = """ SELECT 
                  CONCAT(mp.FirstName, ' ', mp.FamilyName) AS MemberName,
                  s.*
                  FROM Subscriptions s
                  INNER JOIN MemberProfiles mp ON s.MemberID = mp.UserID
                  WHERE DATEDIFF(s.EndDate, CURDATE()) BETWEEN 0 AND 7
                  AND s.subscriptionStatus = 'Active';

                """
        cur.execute(sql)
        subs_endsoon = cur.fetchall()
        return subs_endsoon
# get subscriptions ended last 60days
def get_subs_end():
     cur = getCursor()
     sql = """ SELECT 
                  CONCAT(mp.FirstName, ' ', mp.FamilyName) AS MemberName,
                  s.*
                  FROM Subscriptions s
                  INNER JOIN MemberProfiles mp ON s.MemberID = mp.UserID
                  WHERE DATEDIFF(CURDATE(), s.EndDate) BETWEEN 0 AND 60
                  AND s.subscriptionStatus = 'Inactive';

                """
     cur.execute(sql)
     subs_end = cur.fetchall()
     return subs_end

@app.route("/subscriptions")
@require_role(3)
def sub_list():
       sub_endsoon = get_subs_endsoon()
       sub_end = get_subs_end()
       return render_template('manager/subscriptions_ending.html',sub_endsoon = sub_endsoon, sub_end = sub_end, format_date = format_date)

@app.route("/send/notification/<int:id>")
@require_role(3)
def send_notification(id):
    connection=getDbConnection() 
   # set up a 
    cur = getCursor()
    sql = """
            UPDATE Subscriptions s SET Reminder = "Yes"
            WHERE SubscriptionID = %s and DATEDIFF(s.EndDate, CURDATE()) BETWEEN 0 AND 7;
            """
    cur.execute(sql,(id,))
    connection.commit()
    flash('You have sent a reminder to this member!','success')
    return redirect(url_for('sub_list'))


@app.route("/addnews", methods=['GET','POST'])
@require_role(3)
def addnews():
    if request.method == "POST":
        title = request.form["title"]
        news = request.form["news"]
        cursor = getCursor()
        cursor.execute("INSERT INTO News(Title, News, LastUpdatedBy, LastUpdatedDate) VALUES (%s, %s, %s, %s);", \
                       (title, news, session['id'], datetime.now(),))
        return redirect("/news")
    else:    
        return render_template("manager/add_news.html")

@app.route("/editnews/<int:id>", methods=["GET","POST"])
@require_role(3)
def editnews(id):
    if request.method == "POST":
        title = request.form["title"]
        news = request.form["news"]
        cursor = getCursor()
        cursor.execute("UPDATE News SET Title = %s, News = %s, LastUpdatedBy = %s, LastUpdatedDate = %s WHERE NewsID = %s;", \
                       (title, news, session['id'], datetime.now(), id))
        return redirect("/news")
    else:
        cursor = getCursor()
        cursor.execute("SELECT * FROM News WHERE NewsID = %s", (id,))
        news = cursor.fetchone()
        return render_template("manager/edit_news.html", news = news)

@app.route("/deletenews/<int:id>", methods=["GET","POST"])
@require_role(3)
def deletenews(id):
    cursor = getCursor()
    cursor.execute("DELETE FROM News WHERE NewsID = %s;", (id,))
    return redirect("/news")

@app.route('/attendance_report')
@require_role(3)
def attendance_report():
    return render_template('manager/attendance_report.html')

@app.route('/get_members')
@require_role(3)
def get_members():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT UserID, CONCAT(FirstName, ' ', FamilyName) AS FullName
        FROM MemberProfiles
    """)
    members = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(members)

@app.route('/overall_attendance')
@require_role(3)
def overall_attendance():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT MP.UserID, CONCAT(MP.FirstName, ' ', MP.FamilyName) AS FullName, COUNT(A.Attended) AS TotalAttendance
        FROM MemberProfiles MP
        JOIN Attendance A ON MP.UserID = A.MemberID
        GROUP BY MP.UserID
    """)
    results = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(results)

@app.route('/individual_attendance/<int:member_id>')
@require_role(3)
def individual_attendance(member_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT A.Date, A.Attended
        FROM Attendance A
        WHERE A.MemberID = %s
    """, (member_id,))
    records = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(records)

@app.route('/financial_report')
@require_role(3)
def financial_report():
    year = request.args.get('year', default=str(datetime.now().year))
    return render_template('manager/financial_report.html', year=year)



@app.route('/financial_report_data')
@require_role(3)
def financial_report_data():
    year = request.args.get('year', default=str(datetime.now().year))
    print(year)
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    results = {}
    try:
        queries = {
            'monthly': """
                SELECT DATE_FORMAT(Date, '%Y-%m') as Month,
                    SUM(CASE WHEN Type='Subscription' THEN Amount ELSE 0 END) as Subscriptions,
                    SUM(CASE WHEN Type='Workshop' THEN Amount ELSE 0 END) as Workshops,
                    SUM(CASE WHEN Type='Lesson' THEN Amount ELSE 0 END) as Lessons
                FROM Payments
                WHERE YEAR(Date) = %s
                GROUP BY Month
                ORDER BY Month
            """,
            'annual_by_type': """
                SELECT Type, SUM(Amount) as Total
                FROM Payments
                WHERE YEAR(Date) = %s
                GROUP BY Type
            """,
               'annual_total': """
                SELECT SUM(Amount) as Total
                FROM Payments
                WHERE YEAR(Date) = %s
            """
        }
        # Fetch monthly data
        cursor.execute(queries['monthly'], (year,))
        results['monthly'] = cursor.fetchall()

        # Fetch annual total by type
        cursor.execute(queries['annual_by_type'], (year,))
        annual_totals = cursor.fetchall()
        results['annual_by_type'] = {item['Type']: item['Total'] for item in annual_totals}
        
        cursor.execute(queries['annual_total'], (year,))
        results['annual_total'] = cursor.fetchone()['Total']
        
    finally:
        cursor.close()
        connection.close()

    return jsonify(results)

@app.route('/report/workshop')
@require_role(3)
def workshop_report():
    cursor = getCursor()
    cursor.execute("""SELECT WorkshopID, Title from Workshops
                    ORDER BY WorkshopID;""")
    workshops = cursor.fetchall()
    workshop_attendance = []

    for workshopID, title in workshops:
        cursor.execute("""SELECT COUNT(*) FROM Attendance WHERE WorkshopID = %s AND Attended = 1;""", (workshopID,))
        attendance_count = cursor.fetchone()[0]
        cursor.execute("""SELECT Capacity, Title FROM Workshops WHERE WorkshopID = %s""",(workshopID,))
        capacity = cursor.fetchone()[0]
        attendance_ratio = "{:.2f}".format(attendance_count / capacity)
        workshop_attendance.append({'WorkshopID': workshopID, 'Title': title, 'AttendanceRatio': attendance_ratio })

    sorted_workshops = sorted(workshop_attendance, key=lambda x: x['AttendanceRatio'], reverse=True)
    sorted_workshops_5 = sorted_workshops[:5]


    
    #chart
    labels = [workshop['Title'] for workshop in sorted_workshops_5]
    data = [workshop['AttendanceRatio'] for workshop in sorted_workshops_5]
    
  
    return render_template('manager/workshop_report.html', workshops=sorted_workshops_5, labels = labels, data = data)

@app.route('/subscriptionprices')
@require_role(3)
def subscriptionprices():
        cursor = getCursor()
        cursor.execute('SELECT * FROM SubscriptionPrices;')
        subscriptionprices = cursor.fetchall()
        return render_template('manager/edit_subscriptionprices.html', subscriptionprices = subscriptionprices)


@app.route('/editsubscriptionprices', methods=["POST"])
@require_role(3)
def editsubscriptionprices():    
        annual = request.form['Annual']
        monthly = request.form['Monthly']
        discount = request.form['Discount(%)']
        cursor = getCursor()
        cursor.execute('UPDATE SubscriptionPrices SET Price = %s WHERE Type = "Annual";', (annual,))
        cursor.execute('UPDATE SubscriptionPrices SET Price = %s WHERE Type = "Monthly";', (monthly,))
        cursor.execute('UPDATE SubscriptionPrices SET Price = %s WHERE Type = "Discount(%)";', (discount,))
        flash('Subscription Fees updated successfully.', 'success')
        return redirect('/subscriptionprices')
    
@app.route('/delete_user/<int:user_id>/<string:return_url>', methods=['POST'])
@require_role(3)
def delete_user(user_id, return_url):
    connection = getDbConnection()
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE Users SET IsDeleted = TRUE WHERE UserID = %s", (user_id,))
        connection.commit()
        flash("User successfully deleted.", "success")
    except Exception as err:
        connection.rollback()
        flash(f"Error deleting user: {err}", "error")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for(return_url))  # Redirect to the user management page
