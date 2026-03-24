const express = require("express");
const cors = require("cors");

const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", service: "backend", timestamp: new Date().toISOString() });
});

app.get("/api/message", (_req, res) => {
  res.json({
    message: "Hello from Express backend",
    timestamp: new Date().toISOString(),
  });
});

app.listen(port, () => {
  console.log(`Backend is running on port ${port}`);
});