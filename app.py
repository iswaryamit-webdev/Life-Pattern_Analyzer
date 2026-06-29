from flask import make_response
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
import pandas as pd
from flask import send_file
from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

app = Flask(__name__)
app.secret_key="mysecretkey"
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Iswarya@2006",
    database="life_pattern"
)

cursor = conn.cursor()

@app.route("/", methods=["GET", "POST"])
def home():

    
    if "user_id" not in session:
        return redirect(url_for("login"))
    print("URL reached")
    print("Method =", request.method)

    if request.method == "POST":
        print("Form Submitted")

    if request.method == "POST":

        log_date = request.form["log_date"]
        sleep = request.form["sleep_hours"]
        study = request.form["study_hours"]
        exercise = request.form["exercise_hours"]
        screen = request.form["screen_time"]
        mood_score = request.form["mood_score"]
        user_id=session["user_id"]
        cursor.execute("""
            INSERT INTO daily_log
            (log_date, sleep_hours, study_hours,
             exercise_hours, screen_time, mood_score, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (log_date, sleep, study, exercise, screen, mood_score,user_id))

        conn.commit()
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/logs")
def logs():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    search_date = request.args.get("search_date")

    if search_date:

        cursor.execute("""
        SELECT log_date,
               sleep_hours,
               study_hours,
               exercise_hours,
               screen_time,
               mood_score,
               id
        FROM daily_log
        WHERE user_id=%s
        AND log_date=%s
        """, (user_id, search_date))

    else:

        cursor.execute("""
        SELECT log_date,
               sleep_hours,
               study_hours,
               exercise_hours,
               screen_time,
               mood_score,
               id
        FROM daily_log
        WHERE user_id=%s
        """, (user_id,))

    data = cursor.fetchall()

    return render_template("logs.html", data=data)

    
@app.route("/delete/<int:id>")
def delete(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cursor.execute(
        "DELETE FROM daily_log WHERE id=%s AND user_id=%s",
        (id, user_id)
    )

    conn.commit()

    return redirect(url_for("logs"))    

@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit(id):

    if request.method == "POST":

        sleep = request.form["sleep_hours"]
        study = request.form["study_hours"]
        exercise = request.form["exercise_hours"]
        screen = request.form["screen_time"]
        mood = request.form["mood_score"]

        cursor.execute("""
        UPDATE daily_log
        SET sleep_hours=%s,
            study_hours=%s,
            exercise_hours=%s,
            screen_time=%s,
            mood_score=%s
        WHERE id=%s
        """,
        (sleep,study,exercise,screen,mood,id))

        conn.commit()

        return redirect(url_for("logs"))

    cursor.execute(
        "SELECT * FROM daily_log WHERE id=%s",
        (id,)
    )

    data = cursor.fetchone()

    return render_template(
        "edit.html",
        row=data
    )

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Username
    cursor.execute(
        "SELECT username FROM users WHERE id=%s",
        (user_id,)
    )

    username = cursor.fetchone()[0]

    # Total Logs
    cursor.execute(
        "SELECT COUNT(*) FROM daily_log WHERE user_id=%s",
        (user_id,)
    )

    total_logs = cursor.fetchone()[0]

    # Most Common Mood
    cursor.execute("""
        SELECT mood_score
        FROM daily_log
        WHERE user_id=%s
        GROUP BY mood_score
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """, (user_id,))

    mood = cursor.fetchone()

    if mood:
        most_common_mood = mood[0]
    else:
        most_common_mood = "No Data"

    # Productivity Score
    cursor.execute("""
        SELECT AVG(sleep_hours),
               AVG(study_hours),
               AVG(exercise_hours),
               AVG(screen_time)
        FROM daily_log
        WHERE user_id=%s
    """, (user_id,))

    data = cursor.fetchone()

    if data[0] is None:
        avg_score = 0
    else:
        avg_score = round(
            data[0]*2 +
            data[1]*3 +
            data[2]*2 -
            data[3],
            1
        )

    return render_template(
        "profile.html",
        username=username,
        total_logs=total_logs,
        most_common_mood=most_common_mood,
        avg_score=avg_score
    )

@app.route("/pdf")
def pdf():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Username
    cursor.execute(
        "SELECT username FROM users WHERE id=%s",
        (user_id,)
    )
    username = cursor.fetchone()[0]

    # Total Logs
    cursor.execute(
        "SELECT COUNT(*) FROM daily_log WHERE user_id=%s",
        (user_id,)
    )
    total_logs = cursor.fetchone()[0]

    # Averages
    cursor.execute("""
        SELECT AVG(sleep_hours),
               AVG(study_hours),
               AVG(exercise_hours),
               AVG(screen_time)
        FROM daily_log
        WHERE user_id=%s
    """, (user_id,))

    data = cursor.fetchone()

    avg_sleep = data[0] or 0
    avg_study = data[1] or 0
    avg_exercise = data[2] or 0
    avg_screen = data[3] or 0

    score = (
        avg_sleep * 2 +
        avg_study * 3 +
        avg_exercise * 2 -
        avg_screen
    )

    # Recommendation
    if avg_sleep < 7:
        recommendation = "Try sleeping at least 7 hours."

    elif avg_screen > 5:
        recommendation = "Reduce screen time for better productivity."

    else:
        recommendation = "Excellent routine. Keep going!"

    # PDF Creation
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            "AI LIFE PATTERN REPORT",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 12))

    content.append(
        Paragraph(
            f"Username: {username}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"Total Logs: {total_logs}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"Average Sleep: {round(avg_sleep,1)} hrs",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"Average Study: {round(avg_study,1)} hrs",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"Average Exercise: {round(avg_exercise,1)} hrs",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"Average Screen Time: {round(avg_screen,1)} hrs",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"Productivity Score: {round(score,1)}",
            styles["Normal"]
        )
    )

    content.append(Spacer(1, 12))

    content.append(
        Paragraph(
            f"Recommendation: {recommendation}",
            styles["Normal"]
        )
    )

    doc.build(content)

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)

    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = \
        "attachment; filename=LifePatternReport.pdf"

    return response

    
@app.route("/chart")
def chart():

    user_id = session["user_id"]

    cursor.execute("""
        SELECT log_date, sleep_hours
        FROM daily_log
        WHERE user_id=%s
        ORDER BY log_date
    """, (user_id,))

    data = cursor.fetchall()

    dates = []
    sleep = []

    for row in data:
        dates.append(str(row[0]))
        sleep.append(float(row[1]))

    return render_template(
        "chart.html",
        dates=dates,
        sleep=sleep
    )


@app.route("/register", methods=["GET", "POST"])
def register():


    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor.execute(
            "INSERT INTO users(username,password) VALUES(%s,%s) ",
            (username, password)
        )

        conn.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cursor.fetchone()
        if user:
            session["name"]=username
            session["user_id"]=user[0]
            return redirect(url_for("dashboard"))

    return render_template("login.html")
@app.route("/logout")
def logout():

    session.pop("user_id", None)
    session.pop("name", None)

    return redirect(url_for("login"))


@app.route("/download")
def download():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cursor.execute("""
        SELECT log_date,
               sleep_hours,
               study_hours,
               exercise_hours,
               screen_time,
               mood_score
        FROM daily_log
        WHERE user_id=%s
    """, (user_id,))

    data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "Date",
            "Sleep Hours",
            "Study Hours",
            "Exercise Hours",
            "Screen Time",
            "Mood"
        ]
    )

    file_name = "LifePatternReport.xlsx"

    df.to_excel(file_name, index=False)

    return send_file(
        file_name,
        as_attachment=True
    )

    
@app.route("/mood_chart")
def mood_chart():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cursor.execute("""
        SELECT mood_score, COUNT(*)
        FROM daily_log
        WHERE user_id=%s
        GROUP BY mood_score
    """, (user_id,))

    data = cursor.fetchall()

    moods = []
    counts = []

    for row in data:
        moods.append(row[0])
        counts.append(row[1])

    return render_template(
        "mood_chart.html",
        moods=moods,
        counts=counts
    )


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id=session["user_id"]    
    
    cursor.execute("select avg(sleep_hours) from daily_log where user_id=%s",(user_id,))
    Average_Sleep=cursor.fetchone()[0]

    cursor.execute("select avg(study_hours) from daily_log where user_id=%s",(user_id,))
    Average_Study=cursor.fetchone()[0]

    cursor.execute("select avg(screen_time) from daily_log where user_id=%s",(user_id,))  
    Average_screen_Time=cursor.fetchone()[0]

    cursor.execute("select avg(exercise_hours) from daily_log where user_id=%s",(user_id,))
    Average_Exercise=cursor.fetchone()[0]

    cursor.execute("select count(*) from daily_log where user_id=%s",(user_id,))
    Total_Logs=cursor.fetchone()[0]

    cursor.execute(
    "select mood_score from daily_log where user_id=%s group by mood_score order by count(*) desc limit 1",
    (user_id,))

    mood_data = cursor.fetchone()

    if mood_data:
      Most_Common_Mood = mood_data[0]
    else:
      Most_Common_Mood = "No Data"
    if Average_Sleep is None:
      return render_template(
        "dashboard.html",
        Average_Sleep=0,
        Average_Study_hours=0,
        Average_Screen_Time=0,
        Average_Exercise_Hours=0,
        Total_Logs=0,
        Most_Common_Mood="No Data",
        score=0,
        status="Add your first log!"
    )
    score = Average_Sleep*2 + Average_Study*3 + Average_Exercise*2 - Average_screen_Time
    recommendation = []

    if Average_Sleep < 7:
        recommendation.append("😴 Increase sleep duration.")

    if Average_screen_Time > 5:
        recommendation.append("📱 Reduce screen time.")

    if Average_Exercise < 0.5:
        recommendation.append("💪 Add more exercise.")

    if Average_Study < 3:
        recommendation.append("📚 Increase study hours.")

    if not recommendation:
        recommendation.append("🎉 Excellent routine. Keep going!")


    return render_template("dashboard.html",  Average_Sleep=round(Average_Sleep,1),
    Average_Study_hours=round(Average_Study,1), Average_Screen_Time=round(Average_screen_Time,1),Average_Exercise_Hours=round(Average_Exercise,1),
    Total_Logs=Total_Logs,Most_Common_Mood=Most_Common_Mood,score=round(score,1),status=recommendation)

@app.route("/score")
def score():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cursor.execute("""
        SELECT sleep_hours,
               study_hours,
               exercise_hours,
               screen_time
        FROM daily_log
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,))

    data = cursor.fetchone()

    if data is None:
        return render_template(
            "score.html",
            score=0,
            status="Add your first log!"
        )

    Average_Sleep = data[0]
    Average_Study = data[1]
    Average_Exercise_Hours = data[2]
    Average_screen_Time = data[3]

    score = (
        Average_Sleep * 2
        + Average_Study * 3
        + Average_Exercise_Hours * 2
        - Average_screen_Time
    )

    if Average_Sleep < 7:
        recommendation = "Try sleeping at least 7 hours."

    elif Average_screen_Time > 5:
        recommendation = "Reduce screen time for better productivity."

    else:
        recommendation = "Excellent routine. Keep going!"

    return render_template(
        "score.html",
        score=round(score, 1),
        status=recommendation
    )
    
if __name__ == "__main__":
    app.run(debug=True)