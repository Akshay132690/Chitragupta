require('dotenv').config();
const express = require('express');
const session = require('express-session');
const passport = require('passport');
const mongoose = require('mongoose');
const GoogleStrategy = require('passport-google-oauth20').Strategy;
const path = require('path');
const fetch = require('node-fetch');
const MongoStore = require('connect-mongo'); // ✅ ADD THIS LINE
const app = express();

// app.use(session({
//   secret: process.env.SESSION_SECRET,
//   resave: false,
//   saveUninitialized: false,
//   store: MongoStore.create({
//     mongoUrl: process.env.MONGO_URL
//   }),
//   cookie: { maxAge: 24 * 60 * 60 * 1000 } // 1 day
// }));

// Added for weather API

// const app = express();

// MongoDB Connection
mongoose.connect(process.env.MONGO_URL)
  .then(() => console.log('MongoDB connected successfully'))
  .catch(err => console.error('MongoDB connection error:', err));

// Import User model
const User = require('./model/user');

// View engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Middleware
app.use(express.static(path.join(__dirname, 'assets'))); // Changed from 'assets' to 'public'
app.use(express.json()); // Added for API routes
app.use(express.urlencoded({ extended: true }));

// Sessions

app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  store: MongoStore.create({
    mongoUrl: process.env.MONGO_URL
  }),
  cookie: { maxAge: 24 * 60 * 60 * 1000 } // 1 day
}));

// Passport init
app.use(passport.initialize());
app.use(passport.session());

// User serialization
passport.serializeUser((user, done) => {
  done(null, user.id);
});

passport.deserializeUser(async (id, done) => {
  try {
    const user = await User.findById(id);
    done(null, user);
  } catch (err) {
    done(err, null);
  }
});

// Passport Google OAuth Strategy
passport.use(new GoogleStrategy({
  clientID: process.env.GOOGLE_CLIENT_ID,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  callbackURL: process.env.CALLBACK_URL
}, async (accessToken, refreshToken, profile, done) => {
  try {
    let user = await User.findOne({ googleId: profile.id });

    if (!user) {
      user = await User.create({
        googleId: profile.id,
        name: profile.displayName,
        email: profile.emails[0].value,
        image: profile.photos[0].value
      });
    }
    return done(null, user);
  } catch (err) {
    return done(err, null);
  }
}));

// Auth check middleware
function ensureAuthenticated(req, res, next) {
  if (req.isAuthenticated()) return next();
  res.redirect('/login');
}

// Routes
app.get('/', (req, res) => {
  res.render('index', { user: req.user, title: 'Home' });
});

app.get('/login', (req, res) => {
  if (req.isAuthenticated()) return res.redirect('/');
  res.render('login', { title: 'Login' });
});

// Weather API endpoint
app.get('/api/weather', async (req, res) => {
  const location = req.query.location;

  if (!location) {
    return res.status(400).json({ error: 'Location required' });
  }

  try {
    const apiKey = process.env.WEATHER_API_KEY;
    const url = `https://api.openweathermap.org/data/2.5/weather?q=${encodeURIComponent(location)}&appid=${apiKey}&units=metric`;
    const response = await fetch(url);
    const data = await response.json();

    if (data.cod !== 200) {
      return res.status(data.cod).json(data);
    }

    res.json(data);
  } catch (error) {
    console.error('Weather API error:', error);
    res.status(500).json({ error: 'Weather API failed' });
  }
});

// NASA APOD API endpoint
app.get('/api/apod', async (req, res) => {
  try {
    const response = await fetch(
      `https://api.nasa.gov/planetary/apod?api_key=${process.env.NASA_API_KEY}`
    );
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('NASA APOD error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch APOD data'
    });
  }
});

// Auth routes
app.get('/auth/google', passport.authenticate('google', {
  scope: ['profile', 'email']
}));

app.get('/auth/google/callback', passport.authenticate('google', {
  failureRedirect: '/login'
}), (req, res) => {
  res.redirect('/');
});

app.get('/logout', (req, res) => {
  req.logout(() => {
    req.session.destroy(() => {
      res.redirect('/');
    });
  });
});

// Protected pages
app.get('/glacier', ensureAuthenticated, (req, res) => {
  res.redirect('http://127.0.0.1:5000'); // redirects browser to Python app
});


app.get('/road', ensureAuthenticated, (req, res) => {
 res.redirect('http://127.0.0.1:5002');
});

app.get('/drainage', ensureAuthenticated, (req, res) => {
 res.redirect('http://127.0.0.1:5001');
});


// GET: Show login form
app.get('/admin-login', ensureAuthenticated , (req, res) => {
  console.log('GET /admin-login called');
  res.render('admin-login', { error: null });
});

// Admin Login POST
app.post('/admin-login', (req, res) => {
  const { password } = req.body;
  if (password === process.env.ADMIN_PASSWORD) {
    req.session.isAdmin = true;
    res.redirect('/admin-dashboard');
  } else {
    res.render('admin-login', { error: 'Incorrect password' });
  }
});


// Admin Dashboard (Protected)
app.get('/admin-dashboard',  async (req, res) => {
  if (!req.session.isAdmin) {
    return res.redirect('/admin-login');
  }

  const users = await User.find();

  // Get all sessions from connect-mongo's default collection: "sessions"
  const raw = await mongoose.connection.collection('sessions').find({}).toArray();

  // Parse & normalize
  const parsed = raw.map(doc => {
    let data = {};
    try { data = JSON.parse(doc.session); } catch {}
    return {
      sessionId: String(doc._id),
      userId: data?.passport?.user ? String(data.passport.user) : null,
      expiresAt: doc.expires ? new Date(doc.expires) : null
    };
  });

  // Pick the latest (by expiry) per user
  const sessionsByUser = {};
  for (const s of parsed) {
    if (!s.userId) continue;
    const prev = sessionsByUser[s.userId];
    if (!prev || ((s.expiresAt || 0) > (prev.expiresAt || 0))) {
      sessionsByUser[s.userId] = s;
    }
  }

  res.render('admin-dashboard', {
    title: 'Admin Dashboard',
    users,
    sessionData: sessionsByUser   // <-- pass per-user session map
  });
});



// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).render('error', {
    title: 'Error',
    message: 'Something went wrong!'
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).render('error', {
    title: 'Not Found',
    message: 'Page not found'
  });
});

//admin section


// Admin Login Page





// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});