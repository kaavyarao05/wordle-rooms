from flask import Flask,render_template,request,session,redirect, url_for
from flask_socketio import join_room,leave_room,send,SocketIO
import random
from string import ascii_uppercase

app=Flask(__name__)
app.config["SECRET_KEY"]='somethingsecurechangel8r'

socketio=SocketIO(app)

rooms:dict={}

def generate_unique_code(length):
    while True:
        code=""
        for _ in range(length):
            code+=random.choice(ascii_uppercase)
        if code not in rooms:
            break
    return code

@app.route("/",methods=["POST","GET"])
def home():
    session.clear()
    if request.method=='POST':
        name=request.form.get("name")
        code=request.form.get("code")
        join=request.form.get("join",False)
        create=request.form.get("create",False)
    
        if not name:
            return render_template("home.html",error="Please enter a name")

        if join != False and not code:
            return render_template("home.html",name=name,code=code,error="Please enter a room code")
        
        room=code
        if create != False:
            room=generate_unique_code(4)
            rooms[room]={'members':0,"messages":[],"word":""}
        elif code not in rooms:
            return render_template("home.html",name=name,code=code,error="Room does not exist")
        
        session['room']=room
        session['name']=name
        
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route('/room')
def room():
    room=session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    
    if rooms[room]['messages']:
        return render_template("room.html",room=room,messages=rooms[room]['messages'])
    else:
        return render_template("room.html",room=room)


@socketio.on("connect")
def connect(auth):
    room=session.get("room")
    name=session.get("name")
    if not name or not room:
        return
    if room not in rooms:
        leave_room(room)
        return
    join_room(room)
    send(
        {"name":name,
         "message":"has entered the room"},
         to=room)
    rooms[room]['members']+=1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room=session.get("room")
    name=session.get("name")
    leave_room(room)
    if room in rooms:
        rooms[room]['members']-=1
        if rooms[room]['members']==0:
            del rooms[room]
    send(
        {"name":name,
         "message":"has left the room"},
         to=room)
    print(f"{name} left room {room}")

def parse(msg:str,room):
    words=msg.split()
    if len(words)>1:
        if words[0]==r"/wordle":
            if len(words[1])!=5:
                return f"Word doesnt have 5 letters!"
            oldWord=rooms[room]['word']
            rooms[room]['word']=words[1]
            if oldWord=='':
                return f"selected a new <b>Word!</b>"
            return f"selected a new <b>Word!</b> The old word was <b>{oldWord}</b>"
        elif words[0]==r"/guess":
            if len(words[1])!=5:
                return f"Guess doesnt have 5 letters!"
            guessText=''
            green=0
            for i in range(len(words[1])):
                letter=words[1][i]
                if letter==rooms[room]['word'][i]:
                    guessText+=f'<span class="g">{letter}</span>'
                    green+=1
                elif letter in rooms[room]['word']:
                    guessText+=f'<span class="y">{letter}</span>'
                else:
                    guessText+=letter
            if green==5:
                guessText="Congrats You got it!: "+guessText
                rooms[room]['word']=''
            return guessText
            
            
    return msg

@socketio.on("message")
def message(data):
    room=session.get("room")
    if room not in rooms:
        return
    content={
        "name":session.get("name"),
        "message":parse(data["data"],room)
    }
    send(content,to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get("name")}: {data['data']}")

if __name__=="__main__":
    socketio.run(app,debug=True)