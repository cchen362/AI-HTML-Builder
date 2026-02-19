import { useState } from 'react';
import { promptTemplates, type PromptTemplate } from '../../data/promptTemplates';
import './TemplateCards.css';

interface TemplateCardsProps {
  onSelectTemplate: (template: PromptTemplate) => void;
}

const TEMPLATE_ICONS: Record<string, string> = {
  'impact-assessment': '📊',
  'documentation': '📖',
  'dashboard': '📈',
  'project-report': '🗓️',
  'process-documentation': '🔄',
  'presentation': '🎬',
  'stakeholder-brief': '📝',
  'brd': '📐',
};

const TemplateCards: React.FC<TemplateCardsProps> = ({
  onSelectTemplate,
}) => {
  const [showAll, setShowAll] = useState(false);
  const visibleTemplates = showAll ? promptTemplates : promptTemplates.slice(0, 4);

  return (
    <div className="template-cards">
      <div className="template-cards-grid">
        {visibleTemplates.map((t) => (
          <button
            key={t.id}
            className="template-card"
            onClick={() => onSelectTemplate(t)}
            type="button"
          >
            <span className="template-card-icon">
              {TEMPLATE_ICONS[t.id] || '📄'}
            </span>
            <span className="template-card-title">{t.name}</span>
            <span className="template-card-desc">{t.description}</span>
          </button>
        ))}
      </div>
      {!showAll && promptTemplates.length > 4 && (
        <button
          type="button"
          className="template-show-all"
          onClick={() => setShowAll(true)}
        >
          Browse all templates &rarr;
        </button>
      )}
    </div>
  );
};

export default TemplateCards;
