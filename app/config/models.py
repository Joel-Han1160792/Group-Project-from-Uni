from app.config.database import getDbConnection
from app.config.database import getCursor

# get_all functions 

def get_tutors_for_dropdown():
    # Fetch tutors from the database
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT UserID, CONCAT(Title, FirstName, FamilyName) AS FullName FROM TutorProfiles")
        tutors = cursor.fetchall()
        return tutors
    finally: 
        cursor.close()
        connection.close()        

def get_all_locations(available): 
    cursor = getCursor()
    if(available):
        cursor.execute('SELECT * from Location where available = 1')
    else:
        cursor.execute('SELECT * from Location')
    
   
    
    locationList = cursor.fetchall()
    return locationList

def get_all_workshops():   
    cursor = getCursor()
    cursor.execute('SELECT w.workshopid, w.details, w.location, w.date, w.time, w.cost, w.capacity, t.userId, t.firstname,t.familyname FROM Workshops w inner join TutorProfiles t on w.tutorId = t.userId where date > now() ;')
    workshopList = cursor.fetchall()
    return workshopList

def get_all_tutors():
    cursor = getCursor()
    cursor.execute('''
    SELECT tp.* 
    FROM TutorProfiles tp
    JOIN Users u ON tp.UserID = u.UserID
    WHERE u.IsDeleted = FALSE OR u.IsDeleted IS NULL;
    ''')
    tutorlist = cursor.fetchall()
    return tutorlist

def get_all_members():
    cursor = getCursor()
    cursor.execute('''
    SELECT mp.* 
    FROM MemberProfiles mp
    JOIN Users u ON mp.UserID = u.UserID
    WHERE u.IsDeleted = FALSE OR u.IsDeleted IS NULL;
    ''')

    memberlist = cursor.fetchall()
    return memberlist