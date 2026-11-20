const admin = db.getSiblingDB("admin");
const checkins = db.getSiblingDB("gowalla").checkins;
const distribution = admin.aggregate([
  {$shardedDataDistribution: {}},
  {$match: {ns: "gowalla.checkins"}},
]).toArray();
const trajectory = checkins.find({user_id: 0})
  .sort({ts: -1, _id: -1}).limit(201).explain("executionStats");
const window = [[-97.81, 30.22], [-97.74, 30.22], [-97.74, 30.30],
                [-97.81, 30.30], [-97.81, 30.22]];
const region = checkins.find({
  ts: {$gte: ISODate("2010-10-19T23:55:27Z"), $lt: ISODate("2010-10-19T23:55:28Z")},
  loc: {$geoWithin: {$geometry: {type: "Polygon", coordinates: [window]}}},
}).sort({ts: -1, _id: -1}).limit(201).explain("executionStats");

print(EJSON.stringify({
  total_count: checkins.countDocuments({}),
  distribution,
  trajectory,
  region,
}, null, 2));
