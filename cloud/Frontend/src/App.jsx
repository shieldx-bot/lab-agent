import { useEffect, useState } from "react";

export default function App() {
  const [message, setMessage] = useState("Loading...");
  const [error, setError] = useState("");

  useEffect(() => {
    const loadMessage = async () => {
      try {
        const response = await fetch("/api/message");
        if (!response.ok) {
          throw new Error(`Request failed: ${response.status}`);
        }
        const data = await response.json();
        setMessage(`${data.message} (${data.timestamp})`);
      } catch (err) {
        setError(err.message);
      }
    };

    loadMessage();
  }, []);

  return (
    <main className="container">
      <h1>React + Express Docker Demo</h1>
      <p className="status">Backend response: {message}</p>
      {error && <p className="error">Error: {error}</p>}
    </main>
  );
}