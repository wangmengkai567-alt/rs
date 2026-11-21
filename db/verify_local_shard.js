const admin = db.getSiblingDB("admin");
const checkins = db.getSiblingDB("gowalla").checkins;
const hello = admin.runCommand({hello: 1});

if (!hello.isWritablePrimary || !["shard1", "shard2"].includes(hello.setName)) {
  throw new Error("Connect directly to the local shard primary");
}

const config = admin.runCommand({replSetGetConfig: 1}).config;
if (config.members.length !== 1 || config.members[0].host !== hello.me) {
  throw new Error("Replica configuration does not match this primary");
}

const count = checkins.countDocuments({});
if (count <= 0) throw new Error("No local Gowalla documents were found");
const first = checkins.find().sort({_id: 1}).limit(1).next();
print(EJSON.stringify({
  replica_set: hello.setName,
  advertised_member: hello.me,
  namespace: "gowalla.checkins",
  documents: count,
  sample: {source_line: first._id, user_id: first.user_id, timestamp: first.ts},
}, null, 2));
