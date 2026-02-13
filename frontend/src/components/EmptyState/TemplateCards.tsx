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
  return (
    <div className="template-cards">
      <p className="template-cards-heading">
        Quick start with a template, or type your own prompt below
      </p>
      <div className="template-cards-grid">
        {promptTemplates.map((t) => (
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
    </div>
  );
};

export default TemplateCards;
