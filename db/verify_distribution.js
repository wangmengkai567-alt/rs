const admin = db.getSiblingDB("admin");
const store = db.getSiblingDB("gowalla");
const manifest = store.dataset.findOne({_id: "current", status: "ready"});
if (!manifest) throw new Error("Complete the data import before verifying");
if (admin.runCommand({hello: 1}).msg !== "isdbgrid") {
  throw new Error("Run the cluster verification through mongos");
}
const checkins = store.checkins;
const shardList = admin.runCommand({listShards: 1}).shards;
const distribution = admin.aggregate([
  {$shardedDataDistribution: {}},
  {$match: {ns: "gowalla.checkins"}},
]).toArray();
if (distribution.length !== 1) throw new Error("Missing checkins distribution");

const trajectory = checkins.find({user_id: 0})
  .sort({ts: -1, _id: -1}).limit(201).explain("executionStats");
const window = [[-97.81, 30.22], [-97.74, 30.22], [-97.74, 30.30],
                [-97.81, 30.30], [-97.81, 30.22]];
const regionFilter = {
  ts: {$gte: ISODate("2010-10-19T23:55:27Z"), $lt: ISODate("2010-10-19T23:55:28Z")},
  loc: {$geoWithin: {$geometry: {type: "Polygon", coordinates: [window]}}},
};
const region = checkins.find(regionFilter)
  .sort({ts: -1, _id: -1}).limit(201).explain("executionStats");

function routedShards(plan) {
  const shards = plan.queryPlanner.winningPlan.shards;
  if (!Array.isArray(shards)) throw new Error("Plan does not show routing information");
  return shards.map(shard => shard.shardName).sort();
}

const raw = manifest.quality_report;
print(EJSON.stringify({
  input_count: raw.input_count,
  clean_count: raw.clean_count,
  reject_count: raw.reject_count,
  version: manifest.version,
  total_count: checkins.countDocuments({}),
  shard_hosts: shardList.map(shard => ({name: shard._id, connection: shard.host})),
  distribution,
  trajectory_shards: routedShards(trajectory),
  trajectory_user_0_count: checkins.countDocuments({user_id: 0}),
  region_shards: routedShards(region),
  region_source_line_1_found: checkins.findOne({...regionFilter, _id: 1}, {_id: 1}) !== null,
  trajectory,
  region,
}, null, 2));
