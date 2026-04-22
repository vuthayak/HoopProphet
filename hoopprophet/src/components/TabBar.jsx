import React from 'react';

export default function TabBar({ tabs, activeTab, onTabChange }) {
  return (
    <div className="flex border-b border-border overflow-x-auto">
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-4 py-2 text-sm font-medium transition-all duration-150 whitespace-nowrap ${
            activeTab === tab.id
              ? 'text-prob-high border-b-2 border-prob-high'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}