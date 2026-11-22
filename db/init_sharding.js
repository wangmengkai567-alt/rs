const admin = db.getSiblingDB("admin");
const plannedShards = {
  shard1: "shard1/shard1:27011",
  shard2: "shard2/shard2:27021",
};
const currentShards = admin.runCommand({listShards: 1}).shards;
for (const shard of currentShards) {
  if (plannedShards[shard._id] !== shard.host) {
    throw new Error(`Unexpected shard configuration for ${shard._id}`);
  }
}
for (const [name, host] of Object.entries(plannedShards)) {
  if (!currentShards.some(shard => shard._id === name)) {
    admin.runCommand({addShard: host, name});
  }
}

const namespace = "gowalla.checkins";
let metadata = db.getSiblingDB("config").collections.findOne({_id: namespace});
if (!metadata) {
  admin.runCommand({
    shardCollection: namespace,
    key: {user_id: "hashed"},
  });
  metadata = db.getSiblingDB("config").collections.findOne({_id: namespace});
}
if (!metadata || metadata.key.user_id !== "hashed" ||
    Object.keys(metadata.key).length !== 1 || metadata.unsplittable || metadata.unique) {
  throw new Error("Unexpected shard key for gowalla.checkins");
}
print("gowalla.checkins is sharded by user_id");
