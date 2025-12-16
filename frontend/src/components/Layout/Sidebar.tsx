import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useConversationStore } from '@/stores/conversationStore';
import {
  Plus,
  Search,
  MessageSquare,
  Folder,
  FolderPlus,
  MoreVertical,
  Trash2,
  Edit2,
  Archive,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import clsx from 'clsx';

interface SidebarProps {
  onConversationSelect?: () => void;
}

export default function Sidebar({ onConversationSelect }: SidebarProps) {
  const [showGroupInput, setShowGroupInput] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  
  const navigate = useNavigate();
  const { conversationId } = useParams();
  
  const {
    conversations,
    groups,
    selectedGroupId,
    searchQuery,
    setSearchQuery,
    setSelectedGroupId,
    createConversation,
    createGroup,
    deleteConversation,
    searchConversations,
  } = useConversationStore();

  const handleNewConversation = async () => {
    const conv = await createConversation(undefined, selectedGroupId ?? undefined);
    navigate(`/chat/${conv.id}`);
    onConversationSelect?.();
  };

  const handleCreateGroup = async () => {
    if (newGroupName.trim()) {
      await createGroup(newGroupName.trim());
      setNewGroupName('');
      setShowGroupInput(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    searchConversations();
  };

  const handleDeleteConversation = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('确定要删除这个对话吗？')) {
      await deleteConversation(id);
      if (Number(conversationId) === id) {
        navigate('/');
      }
    }
    setMenuOpenId(null);
  };

  // Group conversations by group_id
  const ungroupedConversations = conversations.filter((c) => !c.group_id);
  const groupedConversations = groups.map((group) => ({
    ...group,
    conversations: conversations.filter((c) => c.group_id === group.id),
  }));

  return (
    <div className="flex flex-col h-[calc(100%-3.5rem)]">
      {/* Search */}
      <div className="p-3">
        <form onSubmit={handleSearch} className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索对话..."
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </form>
      </div>

      {/* New conversation button */}
      <div className="px-3 mb-2">
        <button
          onClick={handleNewConversation}
          className="w-full flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium transition"
        >
          <Plus className="w-5 h-5" />
          新建对话
        </button>
      </div>

      {/* Groups and conversations */}
      <div className="flex-1 overflow-y-auto px-3 pb-3">
        {/* All conversations option */}
        <button
          onClick={() => setSelectedGroupId(null)}
          className={clsx(
            'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition',
            selectedGroupId === null
              ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
          )}
        >
          <MessageSquare className="w-4 h-4" />
          全部对话
        </button>

        {/* Groups */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
              分组
            </span>
            <button
              onClick={() => setShowGroupInput(true)}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <FolderPlus className="w-4 h-4 text-gray-400" />
            </button>
          </div>

          {showGroupInput && (
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                placeholder="分组名称"
                className="flex-1 px-3 py-1.5 text-sm rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleCreateGroup();
                  if (e.key === 'Escape') setShowGroupInput(false);
                }}
              />
              <button
                onClick={handleCreateGroup}
                className="px-3 py-1.5 text-sm rounded bg-primary-500 text-white"
              >
                添加
              </button>
            </div>
          )}

          {groups.map((group) => (
            <button
              key={group.id}
              onClick={() => setSelectedGroupId(group.id)}
              className={clsx(
                'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition',
                selectedGroupId === group.id
                  ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              )}
            >
              <Folder className="w-4 h-4" />
              {group.name}
              <span className="ml-auto text-xs text-gray-400">
                {groupedConversations.find((g) => g.id === group.id)?.conversations.length || 0}
              </span>
            </button>
          ))}
        </div>

        {/* Conversations list */}
        <div className="mt-4">
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-2 block">
            对话
          </span>

          <div className="space-y-1">
            {(selectedGroupId === null ? conversations : conversations.filter(c => c.group_id === selectedGroupId)).map((conv) => (
              <div
                key={conv.id}
                className={clsx(
                  'group relative rounded-lg transition cursor-pointer',
                  Number(conversationId) === conv.id
                    ? 'bg-primary-50 dark:bg-primary-900/20'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                )}
              >
                <button
                  onClick={() => {
                    navigate(`/chat/${conv.id}`);
                    onConversationSelect?.();
                  }}
                  className="w-full text-left px-3 py-2"
                >
                  <p
                    className={clsx(
                      'text-sm font-medium truncate',
                      Number(conversationId) === conv.id
                        ? 'text-primary-600 dark:text-primary-400'
                        : 'text-gray-900 dark:text-white'
                    )}
                  >
                    {conv.title}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {formatDistanceToNow(new Date(conv.updated_at.endsWith('Z') ? conv.updated_at : conv.updated_at + 'Z'), {
                      addSuffix: true,
                      locale: zhCN,
                    })}
                  </p>
                  {conv.tags && conv.tags.length > 0 && (
                    <div className="flex gap-1 mt-1 flex-wrap">
                      {conv.tags.slice(0, 3).map((tag, i) => (
                        <span
                          key={i}
                          className="px-1.5 py-0.5 text-xs rounded bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </button>

                {/* Menu button */}
                <div className="absolute right-2 top-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuOpenId(menuOpenId === conv.id ? null : conv.id);
                    }}
                    className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-600"
                  >
                    <MoreVertical className="w-4 h-4 text-gray-400" />
                  </button>

                  {menuOpenId === conv.id && (
                    <>
                      <div
                        className="fixed inset-0 z-40"
                        onClick={() => setMenuOpenId(null)}
                      />
                      <div className="absolute right-0 mt-1 w-36 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            // TODO: Edit title
                            setMenuOpenId(null);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          <Edit2 className="w-4 h-4" />
                          编辑
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            // TODO: Archive
                            setMenuOpenId(null);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          <Archive className="w-4 h-4" />
                          归档
                        </button>
                        <button
                          onClick={(e) => handleDeleteConversation(conv.id, e)}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          <Trash2 className="w-4 h-4" />
                          删除
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            ))}

            {conversations.length === 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                暂无对话
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
