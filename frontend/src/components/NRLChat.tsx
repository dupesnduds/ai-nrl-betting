import React, { useState } from 'react';
import './NRLChat.css';
import { useAuth } from '../contexts/AuthContext';

interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
}

const teams = [
  'Broncos', 'Raiders', 'Rabbitohs', 'Roosters', 'Storm', 'Eels', 'Sharks', 'Cowboys',
  'Titans', 'Warriors', 'Knights', 'Sea Eagles', 'Bulldogs', 'Panthers', 'Tigers', 'Dolphins'
];

const NRLChat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [teamA, setTeamA] = useState('Broncos');
  const [teamB, setTeamB] = useState('Raiders');
  const [matchDate, setMatchDate] = useState('2025-04-15');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { currentUser } = useAuth();

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      let token = null;
      if (currentUser) {
        try {
          token = await currentUser.getIdToken();
        } catch (err) {
          console.error('Failed to get Firebase token:', err);
        }
      }

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch('http://localhost:8009/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          user_input: input,
          team_a: teamA,
          team_b: teamB,
          match_date: matchDate
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const data = await response.json();
      const botMessage: ChatMessage = { sender: 'bot', text: data.response };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err: any) {
      console.error(err);
      setError('Failed to get response. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="nrl-chat-container">
      <div className="nrl-chat-history">
        {messages.map((msg, idx) => (
          <div key={idx} className={`nrl-chat-message ${msg.sender}`}>
            {msg.text}
          </div>
        ))}
        {loading && <div className="nrl-chat-message bot">Thinking...</div>}
      </div>
      {error && <div className="nrl-chat-error">{error}</div>}
      <div className="nrl-chat-input-container">
        <select value={teamA} onChange={(e) => setTeamA(e.target.value)}>
          {teams.map((team) => (
            <option key={team} value={team}>{team}</option>
          ))}
        </select>
        <select value={teamB} onChange={(e) => setTeamB(e.target.value)}>
          {teams.map((team) => (
            <option key={team} value={team}>{team}</option>
          ))}
        </select>
        <input
          type="date"
          value={matchDate}
          onChange={(e) => setMatchDate(e.target.value)}
        />
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a match..."
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button onClick={sendMessage} disabled={loading}>Send</button>
      </div>
    </div>
  );
};

export default NRLChat;
