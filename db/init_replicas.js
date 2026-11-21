if (!process.env.GOWALLA_A_IP || !process.env.GOWALLA_B_IP ||
    process.env.GOWALLA_A_IP === process.env.GOWALLA_B_IP) {
  throw new Error("Configure distinct LAN addresses for computers A and B");
}

const replicas = [
  {name: "cfg", host: "gowalla-cfg:27019", configServer: true},
  {name: "shard1", host: "gowalla-shard1:27011", configServer: false},
  {name: "shard2", host: "gowalla-shard2:27021", configServer: false},
];

function connect(replica) {
  const deadline = Date.now() + 90000;
  while (Date.now() < deadline) {
    try {
      const db = new Mongo(
        `mongodb://${replica.host}/?directConnection=true&serverSelectionTimeoutMS=2000`
      ).getDB("admin");
      db.runCommand({ping: 1});
      return db;
    } catch (error) {
      print(`Waiting for ${replica.name}: ${error.message}`);
      sleep(1500);
    }
  }
  throw new Error(`Could not connect to ${replica.host}`);
}

const members = replicas.map(replica => {
  const db = connect(replica);
  let config;
  try {
    config = db.runCommand({replSetGetConfig: 1}).config;
  } catch (error) {
    if (error.codeName !== "NotYetInitialized" && error.code !== 94) throw error;
  }
  if (!config) {
    config = {_id: replica.name, members: [{_id: 0, host: replica.host}]};
    if (replica.configServer) config.configsvr = true;
    db.runCommand({replSetInitiate: config});
  }
  if (config._id !== replica.name || config.members.length !== 1 ||
      config.members[0].host !== replica.host ||
      Boolean(config.configsvr) !== replica.configServer) {
    throw new Error(`Unexpected replica set configuration for ${replica.name}`);
  }
  return {replica, db};
});

for (const {replica, db} of members) {
  const deadline = Date.now() + 90000;
  while (Date.now() < deadline && !db.hello().isWritablePrimary) sleep(1000);
  if (!db.hello().isWritablePrimary) throw new Error(`No primary for ${replica.name}`);
  print(`${replica.name} primary is ready`);
}
