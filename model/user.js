const mongoose = require('mongoose');

const UserSchema = new mongoose.Schema({
   googleId: String,  // ✅ to store Google ID
  name: String,
  email: String,
  image: String,
  password: String
});

module.exports = mongoose.model('User', UserSchema);
