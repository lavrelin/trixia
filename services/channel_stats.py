# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from config import Config
import pytz

logger = logging.getLogger(__name__)

# Timezone Будапешта
BUDAPEST_TZ = pytz.timezone('Europe/Budapest')

class ChannelStatsService:
    """Сервис для сбора статистики каналов и хeatmap активности"""
    
    def __init__(self):
        self.bot = None
        self.previous_stats = {}  # Хранилище предыдущей статистики
        self.chat_messages = {}   # Счетчик сообщений в чатах
        self.hourly_activity = {} # Heatmap активности по часам
    
    def set_bot(self, bot):
        """Устанавливает экземпляр бота"""
        self.bot = bot
        logger.info("Bot instance set for channel stats service")
    
    async def get_channel_stats(self, channel_id: int, channel_name: str) -> Dict[str, Any]:
        """Получить статистику канала"""
        try:
            if not self.bot:
                logger.warning("Bot instance not set")
                return None
            
            # Получаем информацию о чате
            chat = await self.bot.get_chat(channel_id)
            
            # Получаем количество участников
            try:
                member_count = await self.bot.get_chat_member_count(channel_id)
            except Exception as e:
                logger.warning(f"Could not get member count for {channel_name}: {e}")
                member_count = None
            
            # Вычисляем изменения
            previous_count = self.previous_stats.get(channel_name, {}).get('member_count', 0)
            change = member_count - previous_count if member_count and previous_count else 0
            
            stats = {
                'name': channel_name,
                'title': chat.title,
                'member_count': member_count,
                'previous_count': previous_count,
                'change': change,
                'type': chat.type,
                'timestamp': datetime.now(BUDAPEST_TZ)
            }
            
            # Сохраняем текущую статистику для следующего сравнения
            self.previous_stats[channel_name] = {
                'member_count': member_count,
                'timestamp': datetime.now(BUDAPEST_TZ)
            }
            
            logger.info(f"Stats collected for {channel_name}: {member_count} members")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats for {channel_name} ({channel_id}): {e}")
            return {
                'name': channel_name,
                'error': str(e),
                'timestamp': datetime.now(BUDAPEST_TZ)
            }
    
    async def get_chat_message_stats(self, chat_id: int, chat_name: str) -> Dict[str, Any]:
        """Получить статистику сообщений в чате"""
        try:
            # Получаем статистику из счетчика
            message_count = self.chat_messages.get(chat_id, {}).get('count', 0)
            last_reset = self.chat_messages.get(chat_id, {}).get('last_reset', datetime.now(BUDAPEST_TZ))
            
            # Вычисляем период
            hours_since_reset = (datetime.now(BUDAPEST_TZ) - last_reset).total_seconds() / 3600
            
            stats = {
                'name': chat_name,
                'message_count': message_count,
                'hours_since_reset': round(hours_since_reset, 1),
                'messages_per_hour': round(message_count / hours_since_reset, 1) if hours_since_reset > 0 else 0,
                'timestamp': datetime.now(BUDAPEST_TZ)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting message stats for {chat_name}: {e}")
            return {
                'name': chat_name,
                'error': str(e),
                'timestamp': datetime.now(BUDAPEST_TZ)
            }
    
    def increment_message_count(self, chat_id: int):
        """Увеличить счетчик сообщений для чата"""
        if chat_id not in self.chat_messages:
            self.chat_messages[chat_id] = {
                'count': 0,
                'last_reset': datetime.now(BUDAPEST_TZ)
            }
        
        self.chat_messages[chat_id]['count'] += 1
        
        # НОВОЕ: Добавляем в heatmap активности
        current_hour = datetime.now(BUDAPEST_TZ).hour
        chat_name = self._get_chat_name_by_id(chat_id)
        
        if chat_name not in self.hourly_activity:
            self.hourly_activity[chat_name] = {f"{h:02d}:00": 0 for h in range(24)}
        
        self.hourly_activity[chat_name][f"{current_hour:02d}:00"] += 1
    
    def reset_message_count(self, chat_id: int):
        """Сбросить счетчик сообщений для чата"""
        self.chat_messages[chat_id] = {
            'count': 0,
            'last_reset': datetime.now(BUDAPEST_TZ)
        }
    
    def _get_chat_name_by_id(self, chat_id: int) -> str:
        """Получить название чата по ID"""
        chat_names = {
            -1002922212434: "Gambling chat",
            -1002601716810: "Каталог услуг",
            -1003033694255: "Куплю/Отдам/Продам",
            -1002743668534: "Будапешт канал",
            -1002883770818: "Будапешт чат",
            -1002919380244: "Budapest Partners",
        }
        return chat_names.get(chat_id, f"chat_{chat_id}")
    
    async def get_all_stats(self) -> Dict[str, Any]:
        """Собрать статистику по всем каналам и чатам"""
        try:
            all_stats = {
                'timestamp': datetime.now(BUDAPEST_TZ),
                'channels': [],
                'chats': [],
                'heatmap': self.hourly_activity
            }
            
            # Каналы для мониторинга
            channels = {
                'gambling_chat': -1002922212434,
                'catalog': -1002601716810,
                'trade': -1003033694255,
                'budapest_main': -1002743668534,
                'budapest_chat': -1002883770818,
                'partners': -1002919380244,
            }
            
            # Собираем статистику по каналам
            for name, channel_id in channels.items():
                try:
                    stats = await self.get_channel_stats(channel_id, name)
                    if stats:
                        all_stats['channels'].append(stats)
                except Exception as e:
                    logger.error(f"Error collecting stats for {name}: {e}")
                    all_stats['channels'].append({
                        'name': name,
                        'error': str(e)
                    })
            
            # Собираем статистику по чатам (сообщения)
            chat_ids = {
                'gambling_chat': -1002922212434,
                'catalog': -1002601716810,
                'trade': -1003033694255,
                'budapest_main': -1002743668534,
                'budapest_chat': -1002883770818,
                'partners': -1002919380244,
            }
            
            for name, chat_id in chat_ids.items():
                if chat_id:
                    try:
                        stats = await self.get_chat_message_stats(chat_id, name)
                        if stats:
                            all_stats['chats'].append(stats)
                    except Exception as e:
                        logger.error(f"Error collecting message stats for {name}: {e}")
            
            return all_stats
            
        except Exception as e:
            logger.error(f"Error collecting all stats: {e}")
            return {
                'timestamp': datetime.now(BUDAPEST_TZ),
                'error': str(e),
                'channels': [],
                'chats': [],
                'heatmap': {}
            }
    
    def format_stats_message(self, stats: Dict[str, Any]) -> str:
        """Форматировать статистику в красивое сообщение с heatmap"""
        try:
            timestamp = stats['timestamp'].strftime('%d.%m.%Y %H:%M')
            
            message = f"📊 **РАСШИРЕННАЯ СТАТИСТИКА**\n"
            message += f"⏰ {timestamp} (Будапешт)\n\n"
            
            # ============ СТАТИСТИКА КАНАЛОВ ============
            if stats.get('channels'):
                message += "📢 **КАНАЛЫ СООБЩЕСТВА:**\n\n"
                
                channel_emojis = {
                    'gambling_chat': '🐦‍🔥',
                    'catalog': '🙅',
                    'trade': '🕵️‍♂️',
                    'budapest_main': '🙅‍♂️',
                    'budapest_chat': '🙅‍♀️',
                    'partners': '🧶'
                }
                
                for channel in stats['channels']:
                    if 'error' in channel:
                        continue
                    
                    emoji = channel_emojis.get(channel['name'], '📺')
                    title = channel.get('title', channel['name'])
                    count = channel.get('member_count', 'N/A')
                    change = channel.get('change', 0)
                    
                    message += f"{emoji} **{title}**\n"
                    message += f"👥 {count} участников"
                    
                    if change > 0:
                        message += f" 📈 +{change}\n"
                    elif change < 0:
                        message += f" 📉 {change}\n"
                    else:
                        message += f" ➖\n"
                    message += "\n"
            
            # ============ СТАТИСТИКА СООБЩЕНИЙ ============
            if stats.get('chats'):
                message += "💬 **АКТИВНОСТЬ В ЧАТАХ:**\n\n"
                
                total_messages = 0
                avg_per_hour = 0
                
                for chat in stats['chats']:
                    if 'error' in chat:
                        continue
                    
                    count = chat.get('message_count', 0)
                    total_messages += count
                    per_hour = chat.get('messages_per_hour', 0)
                    
                    message += f"📨 **{chat['name']}**\n"
                    message += f"Сообщений: {count} ({per_hour}/час)\n\n"
                
                if stats['chats']:
                    avg_per_hour = round(total_messages / len([c for c in stats['chats'] if 'error' not in c]), 1)
                
                message += f"📊 **Всего сообщений:** {total_messages}\n"
                message += f"📈 **Среднее:** {avg_per_hour}/час\n\n"
            
            # ============ HEATMAP АКТИВНОСТИ ============
            if stats.get('heatmap'):
                message += "🕑 **HEATMAP АКТИВНОСТИ ПО ЧАСАМ (Будапешт):**\n\n"
                
                for chat_name, hourly_data in stats['heatmap'].items():
                    if not hourly_data:
                        continue
                    
                    message += f"**{chat_name.upper()}**\n"
                    
                    # Находим пиковые часы
                    max_hour = max(hourly_data, key=hourly_data.get)
                    max_value = hourly_data[max_hour]
                    
                    # Форматируем heatmap в виде строки
                    heatmap_line = ""
                    for hour in sorted(hourly_data.keys()):
                        value = hourly_data[hour]
                        
                        if value == 0:
                            heatmap_line += "⬜"
                        elif value <= max_value * 0.25:
                            heatmap_line += "🟦"
                        elif value <= max_value * 0.5:
                            heatmap_line += "🟩"
                        elif value <= max_value * 0.75:
                            heatmap_line += "🟨"
                        else:
                            heatmap_line += "🟥"
                    
                    message += heatmap_line + "\n"
                    
                    # Легенда часов
                    hours_legend = "00 04 08 12 16 20\n"
                    message += hours_legend
                    
                    # Пиковое время
                    message += f"🔥 **Пик активности:** {max_hour} ({max_value} сообщений)\n\n"
            
            # ============ СТАТИСТИКА БОТА ============
            from data.user_data import user_data
            message += "🤖 **СТАТИСТИКА БОТА:**\n\n"
            
            total_users = len(user_data)
            active_24h = sum(1 for data in user_data.values() if 
                            datetime.now() - data['last_activity'] <= timedelta(days=1))
            
            message += f"👥 Всего пользователей: {total_users}\n"
            message += f"🟢 Активных за 24ч: {active_24h}\n\n"
            
            message += f"📈 Следующая статистика через {Config.STATS_INTERVAL_HOURS} часов"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting stats message: {e}")
            return f"❌ Ошибка форматирования статистики: {e}"

# Глобальный экземпляр сервиса
channel_stats = ChannelStatsService()
