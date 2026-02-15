import React from 'react';
import SessionCard from './SessionCard';
import TemplateCards from '../EmptyState/TemplateCards';
import ChatInput from '../ChatWindow/ChatInput';
import type { User, SessionSummary } from '../../types';
import type { PromptTemplate } from '../../data/promptTemplates';
import './HomeScreen.css';

interface HomeScreenProps {
  user: User;
  recentSessions: SessionSummary[];
  onSelectSession: (sessionId: string) => void;
  onSelectTemplate: (template: PromptTemplate) => void;
  onSendMessage: (message: string, files?: File[], templateName?: string, userContent?: string) => void;
  onViewAllSessions: () => void;
}

const HomeScreen: React.FC<HomeScreenProps> = ({
  user,
  recentSessions,
  onSelectSession,
  onSelectTemplate,
  onSendMessage,
  onViewAllSessions,
}) => {
  return (
    <div className="home-screen">
      <div className="home-screen-inner">
        <h1 className="home-welcome">
          Welcome back, {user.display_name}
        </h1>

        {recentSessions.length > 0 && (
          <section className="home-section">
            <div className="home-section-label">PICK UP WHERE YOU LEFT OFF</div>
            <div className="home-sessions-row">
              {recentSessions.map((session, i) => (
                <SessionCard
                  key={session.id}
                  session={session}
                  onClick={() => onSelectSession(session.id)}
                  style={{ animationDelay: `${i * 80}ms` }}
                />
              ))}
            </div>
            <button
              type="button"
              className="home-view-all"
              onClick={onViewAllSessions}
            >
              View all sessions &rarr;
            </button>
          </section>
        )}

        <section className="home-section">
          <div className="home-section-label">
            {recentSessions.length > 0 ? 'OR START SOMETHING NEW' : 'START SOMETHING NEW'}
          </div>
          <TemplateCards onSelectTemplate={onSelectTemplate} />
        </section>

        <div className="home-chat-input">
          <ChatInput
            onSendMessage={onSendMessage}
            placeholder="Describe what you want to build..."
          />
        </div>
      </div>
    </div>
  );
};

export default HomeScreen;
