from flask import Flask
from app import app
from flask import render_template, flash
from flask import request
from flask import redirect
from flask import url_for
from flask import session
from app.config.database import getCursor
from flask_hashing import Hashing
from app.config.models import get_all_tutors
from app.config.models import get_all_workshops
from app.config.models import get_all_members
from datetime import datetime
import os
from dateutil.relativedelta import relativedelta
from app.config.helpers import require_role
from app.config.helpers import format_date



hashing = Hashing(app)  #create an instance of hashing

app.secret_key = 'comp639groupAX'

dir_path = os.path.dirname(os.path.realpath(__file__))

@app.route('/')
@app.route('/home')
def home():
    tutorlist = get_all_tutors()
    workshopList = all_available_workshops()
    return render_template('home.html', tutorlist=tutorlist, workshopList= workshopList)

@app.route('/login/' , methods=['GET', 'POST'])
def login():
    msg=""
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:

        # Create variables for easy access
        username = request.form['username']
        user_password = request.form['password']
        # Check if account exists using MySQL
        cursor = getCursor()
        cursor.execute('SELECT Users.UserID, Username, PasswordHash,RoleID, FirstName FROM Users LEFT JOIN ( \
                        select UserID, FirstName from MemberProfiles \
                        union ( select UserID, FirstName from TutorProfiles) \
                        union ( select UserID, FirstName from ManagerProfiles)) AS f ON Users.UserID = f.UserID \
                       WHERE Username = %s', (username,))
        # Fetch one record and return result
        account = cursor.fetchone()
        print(account)
    
        if account is not None:
            password = account[2]
            if hashing.check_value(password, user_password, salt='comp'):
            # If account exists in accounts table 
            # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account[0]
                session['username'] = account[1]
                session['role'] = account[3]
                session['firstname'] = account[4]
                # Redirect to home page
                if session['role'] == 1:
                    return redirect(url_for('member_dashboard'))
                elif session['role'] == 2:
                     return redirect(url_for('tutor_dashboard'))
                else: 
                   return redirect(url_for('manager_dashboard'))
            else:
                #password incorrect
                msg = 'Incorrect password.'
        else:
            # Account doesnt exist or username incorrect
            msg = 'Incorrect username.'
    # Show the login form with message (if any)

    return render_template('login.html', msg = msg)


@app.route("/registerpayment", methods=['post'])
def registerpayment():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Check if account exists using MySQL
        username = request.form['username']
        cursor = getCursor()
        cursor.execute('SELECT * FROM Users WHERE Username = %s', (username,))
        account = cursor.fetchone()
        cursor.fetchall()
        # If account exists show error and validation checks
        if account:
            msg = 'Username already exists.'
            return render_template('register.html', msg = msg)
        else:
            # Create variables for easy access
            username = request.form['username']
            password = request.form['password']
            title = request.form['title']
            firstname = request.form['firstname']
            familyname = request.form['familyname']
            position = request.form['position']
            phonenumber = request.form['phonenumber']
            email = request.form['email']
            address = request.form['address']
            DoB = request.form['DoB']

            session['username'] = username
            session['password'] = password
            session['title'] = title
            session['firstname'] = firstname
            session['familyname'] = familyname
            session['position'] = position
            session['phonenumber'] = phonenumber
            session['email'] = email
            session['address'] = address
            session['DoB'] = DoB

            cursor = getCursor()
            cursor.execute('SELECT * FROM SubscriptionPrices;')
            prices = cursor.fetchall()
            annualfee = prices[0][1]
            monthlyfee = prices[1][1]
            discountfee = prices[2][1]


            return render_template('registerpay.html', annualfee = annualfee, monthlyfee = monthlyfee, discountfee = discountfee  )
    else:
        return redirect("/register")




# this will be the registration page, we need to use both GET and POST requests
@app.route('/register', methods=['GET', 'POST'])
def register():

    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' :
        # Create variables for easy access
        username = session.get('username')
        print(username)
        password = session.get('password')
        print(password)
        title = session.get('title')
        firstname = session.get('firstname')
        familyname = session.get('familyname')
        position = session.get('position')
        phonenumber = session.get('phonenumber')
        email = session.get('email')
        address = session.get('address')
        DoB = session.get('DoB')
        createat = datetime.now()

        cursor = getCursor()
        # Account doesnt exists and the form data is valid, now insert new account into accounts table
        hashed = hashing.hash_value(password, salt='comp')
        cursor.execute('INSERT INTO Users(Username, PasswordHash, RoleID, CreatedAt) VALUES ( %s, %s, %s, %s);', (username, hashed,1,createat,))

        cursorID = getCursor()
        cursorID.execute('SELECT UserID FROM Users WHERE Username = %s', (username,))
        memberID = cursorID.fetchone()[0]

        cursorID.execute('INSERT INTO MemberProfiles (UserID,Title,FirstName,FamilyName,Position,PhoneNumber,Email,Address,DateOfBirth ) VALUES( \
                       %s, %s, %s, %s, %s, %s, %s, %s, %s);', (memberID,title,firstname,familyname,position,phonenumber,email,address, DoB, ))
            

        #if 'image' in session:
        #    image = session.get('image')
        #    global dir_path
        #    img_folder = dir_path + "/static/images"            
        #    image.save(os.path.join(img_folder, image.filename))
        #    cursorID.execute('UPDATE MemberProfiles SET ProfileImage = %s WHERE UserID = %s;', (image.filename, memberID,))
        
        #if 'detail' in session:
        #    detail = session.get('detail')
        #    cursorID.execute('UPDATE MemberProfiles SET MerinoBreedingDetails = %s WHERE UserID = %s;', (detail, memberID,))

        subscription = request.form['subscription']
        amount = request.form['fee']
        months = int(request.form['months'])

                  
        cursorID.execute('SELECT * FROM SubscriptionPrices;')
        prices = cursorID.fetchall()
        annualfee = prices[0][1]
        monthlyfee = prices[1][1]
        discountfee = prices[2][1]

        if subscription == 'Annual':
            fee = annualfee
            if request.form.get('discount') == 'on':
                discount = (discountfee/100) * annualfee
            else:
                discount = 0.00
            enddate = createat.date() + relativedelta(months=12)
        else:
            fee = monthlyfee
            if request.form.get('discount') == "on":
                discount =(discountfee/100) * monthlyfee
            else:
                discount = 0.00
            enddate = createat.date() + relativedelta(months=months)            


        cursorID.execute('INSERT INTO Subscriptions(Type, Fee, Discount, StartDate, EndDate, MemberID) VALUES( \
                       %s, %s, %s, %s, %s, %s);', (subscription,fee,discount,createat.date(), enddate, memberID,))
            
        cursorSubID = getCursor()
        cursorSubID.execute('SELECT SubscriptionID FROM Subscriptions WHERE MemberID = %s;', (memberID,))
        SubID = cursorSubID.fetchone()[0]

        cursorSubID.execute('INSERT INTO Payments(MemberID, SubscriptionID, BookingID, Amount, Date, CreatedAt, Type) VALUES( \
                       %s, %s, NULL, %s, %s, %s, "Subscription");', (memberID, SubID, amount, createat.date(), createat, ))

            
            
        msg = 'You have successfully registered!'

        session.pop('username', None)
        session.pop('password', None)
        session.pop('title', None)
        session.pop('firstname', None)
        session.pop('familyname', None)
        session.pop('position', None)
        session.pop('phonenumber', None)
        session.pop('email', None)
        session.pop('address', None)
        session.pop('DoB', None)
        session.pop('image', None)
        session.pop('detail', None)

        return redirect('/login')
    # Show registration form with message (if any)
    return render_template('register.html')



@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   session.pop('role', None)
   # Redirect to login page
   return redirect(url_for('login'))



def all_available_workshops():
    cursor = getCursor()
    cursor.execute('SELECT w.workshopid, w.details, l.locationName, w.date, w.time, w.cost, w.capacity, t.userId, t.firstname,t.familyname FROM Workshops w inner join TutorProfiles t on w.tutorId = t.userId inner join Location l on l.locationID = w.location where date > now();')
    workshopList = cursor.fetchall()  
    return workshopList

@app.route('/all-workshops')
def all_workshops():
    search_query = request.args.get('search', '')
    if search_query:
        search_query = '%' + search_query + '%'
        cursor = getCursor()
        cursor.execute('SELECT w.workshopid, w.details, w.location, w.date, w.time, w.cost, w.capacity, t.userId, t.firstname,t.familyname, w.title FROM Workshops w inner join TutorProfiles t on w.tutorId = t.userId where date > now() and w.title LIKE %s OR w.details LIKE %s;', (search_query, search_query,))
        workshopList = cursor.fetchall()
    else:
        workshopList = get_all_workshops() 
    return render_template('member/workshop_list.html', workshopList = workshopList)

@app.route('/alltutors')
def alltutors():
    tutorlist = get_all_tutors()
    return render_template('tutor/tutorList.html', tutorlist = tutorlist)

@app.route('/workshop/<int:workshopID>')
def getWorkshop(workshopID):
    cursor = getCursor()
    cursor.execute('SELECT w.WorkshopID, w.Details, w.Location, w.Date, w.Time, w.Cost, w.Capacity, t.UserID, t.FirstName, t.FamilyName FROM Workshops w INNER JOIN TutorProfiles t on w.TutorID = t.UserID WHERE w.WorkshopID = %s;', (workshopID,))
    workshop = cursor.fetchone()
    return render_template('member/workshop.html', workshop = workshop)

@app.route('/tutorprofile/<int:ProfileID>')
def tutorprofileupdate(ProfileID):
    cursor = getCursor()
    cursor.execute('SELECT * FROM TutorProfiles WHERE UserID = %s;', (ProfileID,))
    tutor = cursor.fetchone()
    return render_template('tutor/tutor_profile.html', profile = tutor)

@app.route('/tutorprofile/update', methods=[ 'POST'])
@require_role(3)
def updatetutorprofile():
    profileID = request.form.get("profileID")
    title = request.form.get("title")
    firstname = request.form.get("firstname")
    familyname = request.form.get("familyname")
    position = request.form.get("position")
    phone = request.form.get("phone")
    email = request.form.get("email")
    tutorprofile = request.form.get("tutorprofile")
    cursor = getCursor()
    cursor.execute('UPDATE TutorProfiles SET  Title = %s, FirstName = %s, FamilyName = %s, Position = %s, PhoneNumber = %s, \
                   Email = %s,  TutorProfile = %s  WHERE UserID = %s ', (title,firstname,familyname,position,phone,email,tutorprofile,profileID,))
    image = request.files['image']
    if image:
        global dir_path
        img_folder = dir_path + "/static/images/tutors"            
        image.save(os.path.join(img_folder, image.filename))
        cursor.execute('UPDATE TutorProfiles SET  ProfileImage = %s WHERE UserID = %s ', (image.filename,profileID,))
 
    flash('Tutor profile has been updated successfully.', 'success')
    return redirect(url_for('alltutors'))


@app.route('/allmembers')
@require_role(3)
def allmembers():
    search_query = request.args.get('search', '')
    if search_query:
        search_query = '%' + search_query + '%'
        cursor = getCursor()
        cursor.execute('SELECT  * FROM MemberProfiles WHERE FirstName LIKE %s OR FamilyName LIKE %s;', (search_query, search_query,))
        memberlist = cursor.fetchall()
    else:
        memberlist = get_all_members()
    return render_template('member/memberlist.html', memberlist = memberlist)

@app.route('/memberprofile/<int:UserID>')
@require_role(3)
def memberprofileupdate(UserID):
    cursor = getCursor()
    cursor.execute('SELECT * FROM MemberProfiles WHERE UserID = %s;', (UserID,))
    member = cursor.fetchone()
    return render_template('member/memberProfileUpdate.html', member = member)

@app.route('/memberprofile/update', methods=[ 'POST'])
@require_role(3)
def updatememberprofile():

    UserID = request.form.get("profileID")
    title = request.form.get("title")
    firstname = request.form.get("firstname")
    familyname = request.form.get("familyname")
    position = request.form.get("position")
    phone = request.form.get("phone")
    email = request.form.get("email")
    address = request.form.get("address")
    dateofbirth = request.form.get('dateofbirth')
    details = request.form.get('details')
    cursor = getCursor()
    cursor.execute('UPDATE MemberProfiles SET  Title = %s, FirstName = %s, FamilyName = %s, Position = %s, PhoneNumber = %s, \
                   Email = %s,  Address = %s , DateOfBirth = %s, MerinoBreedingDetails = %s WHERE UserID = %s ', \
                      (title,firstname,familyname,position,phone,email,address,dateofbirth, details, UserID,))
    
    flash('Member profile has been updated successfully.', 'success')
    return redirect(url_for('allmembers'))


# update password
@app.route('/update/password' , methods=['GET', 'POST'])
def update_pwd():
    msg = ""
    if request.method =='POST':
        current_pwd = request.form.get('currentpwd')
        new_pwd = request.form.get('newpwd')
        pwd_check = request.form.get('pwd_check')
        # using session to get username to check current pwd in sql
        username = session.get('username')
        cur = getCursor()
        cur.execute("Select * FROM Users WHERE username = %s;", (username,))
        account = cur.fetchone()
     # check if the current pwd matches with the pwd in database
        hashed_password = hashing.hash_value(current_pwd, salt='comp')
        if hashed_password != account[2]:
            msg = "Please input the correct current password!"
            return render_template('updatepwd.html', msg=msg)
        #check if the user mistakely inputted
        else:
            if new_pwd ==pwd_check:
             hashed_newpwd = hashing.hash_value(new_pwd, salt='comp')
            #update into Users table   
             cur = getCursor()
             cur.execute("UPDATE Users SET PasswordHash = %s WHERE username = %s", (hashed_newpwd, username))
             msg="New Password Saved!"
             return render_template('updatepwd.html', msg=msg)
            else:
                msg="Passwords Inputted Don't Match"
                return render_template('updatepwd.html', msg=msg)
    else:
        return render_template('updatepwd.html',msg=msg)
    

@app.route("/news", methods = ["GET", "POST"])
def news():
    search = request.form.get('search')
    cursor = getCursor()
    print(search)
    if request.method == "POST":
        cursor.execute('SELECT News.NewsID, News.Title, News, FirstName, FamilyName, LastUpdatedDate, ReadNews FROM News \
                        LEFT JOIN ManagerProfiles ON News.LastUpdatedBy = ManagerProfiles.UserID \
                       LEFT JOIN (SELECT * FROM ReadNews WHERE UserID = %s) as usernews  ON usernews.NewsID = News.NewsID \
                       WHERE News.Title LIKE %s \
                       ORDER BY LastUpdatedDate desc; ', (session['id'],f"%{search}%",))
        
    else:
        cursor.execute('SELECT News.NewsID, News.Title, News, FirstName, FamilyName, LastUpdatedDate, ReadNews FROM News \
                        LEFT JOIN ManagerProfiles ON News.LastUpdatedBy = ManagerProfiles.UserID \
                       LEFT JOIN (SELECT * FROM ReadNews WHERE UserID = %s) as usernews  ON usernews.NewsID = News.NewsID \
                       ORDER BY LastUpdatedDate desc; ', (session['id'],))
        
    newslist = cursor.fetchall()
    print(newslist)
    return render_template('manager/view_news.html', newslist = newslist, role = session['role'], format_date=format_date)

@app.route("/markasread/<int:newsid>", methods = ["GET","POST"])
def readnews(newsid):
    cursor = getCursor()
    cursor.execute('INSERT INTO ReadNews VALUES (%s, %s, 1);', (session['id'], newsid))
    return redirect("/news")

@app.route("/markasunread/<int:newsid>", methods = ["GET","POST"])
def unreadnews(newsid):
    cursor = getCursor()
    cursor.execute('DELETE FROM ReadNews WHERE UserID =  %s and NewsID = %s;', (session['id'], newsid))
    return redirect("/news")


@app.route("/favicon.ico")
def favicon():
    return url_for('static', filename='data:,')