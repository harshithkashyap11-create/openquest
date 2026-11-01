require('dotenv').config();
const app = require('./app');
const connectDB = require('./config/db');

const PORT = process.env.PORT || 5000;

// Connect to Database and start server
const startServer = async () => {
  await connectDB();
  app.listen(PORT, () => {
    console.log(`[ClassPulse Backend] Server running on http://localhost:${PORT}`);
    console.log(`[Assessment Endpoint] Ready at POST http://localhost:${PORT}/api/v1/assessments/submit`);
  });
};

startServer();
