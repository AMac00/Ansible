conn = new Mongo("localhost:27017");
ans_db = conn.getDB("ansible_db");


ans_db.createUser(
    {
    user: "{{ ansible_mongo_user }}",
    pwd: "{{ ansible_mongo_pass }}",
    roles: [
        { role: "readWrite", db: "ansible_db"},
        { role: "readWrite", db: "admin"}
    ]
  }
)


//db.adminCommand('listDatabases')

//db.getUsers()

