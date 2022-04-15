from flask import Flask,render_template,request
from pymysql import connections
import os
import boto3
from config import *

app = Flask(__name__)

# DBHOST = os.environ.get("DBHOST")
# DBPORT = os.environ.get("DBPORT")
# DBPORT = int(DBPORT)
# DBUSER = os.environ.get("DBUSER")
# DBPWD = os.environ.get("DBPWD")
# DATABASE = os.environ.get("DATABASE")

bucket= custombucket
region= customregion

db_conn = connections.Connection(
    host= customhost,
    port=3306,
    user= customuser,
    password= custompass,
    db= customdb
)

output = {}

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('AddStudent.html')

@app.route("/about", methods=['POST'])
def about():
    return render_template('www.intellipaat.com')

@app.route("/addstudent", methods=['POST'])
def AddStudent():
    student_id = request.form['student_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    dob = request.form['dob']
    gender = request.form['gender']
    email_id = request.form['email_id']
    phone_no = request.form['phone_no']
    address = request.form['address']
    department = request.form['department']
    skill = request.form['skill']
    student_image_file = request.files['student_image_file']

    insert_sql = "INSERT INTO %s VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if student_image_file.filename == "":
        return "Please select a file"

    try:
        cursor.execute(insert_sql,(student_id, first_name, last_name, dob, gender, email_id, phone_no, address, department, skill))
        db_conn.commit()
        student_name = "" + first_name + " "+ last_name
        # Uplaod image file in S3 #
        student_image_file_name_in_s3 = "student-id-" + str(student_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=student_image_file_name_in_s3, Body=student_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                student_image_file_name_in_s3)

            # Save image file metadata in DynamoDB #
            print("Uploading to S3 success... saving metadata in dynamodb...")

            try:
                dynamodb_client = boto3.client('dynamodb', region_name='us-east-1')
                dynamodb_client.put_item(
                TableName='student_image_table',
                    Item={
                        'studentid': {
                            'N': student_id
                        },
                        'image_url': {
                            'S': object_url
                        }
                    }
                )

            except Exception as e:
                program_msg = "Flask could not update DynamoDB table with S3 object URL"
                return str(e)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddStudentOutput.html', name=student_name)

@app.route("/getstudent", methods=['GET','POST'])
def GetEmp():
        return render_template('GetStudent.html')

@app.route("/fetchdata", methods=['GET','POST'])
def FetchData():
    student_id = request.form['student_id']

    output = {}
    select_sql = "SELECT student_id, first_name, last_name, dob, gender, email_id, phone_no, address, department, skill from student2 where student_id=%s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql,(student_id))
        result = cursor.fetchone()

        output["student_id"] = result[0]
        print('EVERYTHING IS FINE TILL HERE')
        output["first_name"] = result[1]
        output["last_name"] = result[2]
        output["dob"] = result[3]
        output["gender"] = result[4]
        output["email_id"] = result[5]
        output["phone_no"] = result[6]
        output["address"] = result[7]
        output["department"] = result[8]
        output["skill"] = result[9]
        print(output["student_id"])
        dynamodb_client = boto3.client('dynamodb', region_name=customregion)
    
        try:
            response = dynamodb_client.get_item(
                TableName='student_image_table',
                Key={
                    'studentid': {
                        'N': str(student_id)
                    }
                }
            )
            image_url = response['Item']['image_url']['S']

        except Exception as e:
            program_msg = "Flask could not update DynamoDB table with S3 object URL"
            return render_template('AddStudentError.html', errmsg1=program_msg, errmsg2=e)

    except Exception as e:
        print(e)

    finally:
        cursor.close()

    return render_template("GetStudentOutput.html", id=output["emp_id"], fname=output["first_name"], lname=output["last_name"], dob=output["dob"], 
    gender=output["gender"], email=output["email_id"], phone=output["phone_no"], address=output["address"], department=output["department"], 
    skill=output["skill"], image_url=image_url)

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=80,debug=True)
