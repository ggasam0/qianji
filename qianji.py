import random
import time
import logging
from collections import defaultdict
from enum import Enum
from typing import List, Dict, Set, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bluff_game.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Suit(Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"

class Card:
    def __init__(self, rank: str, suit: Suit):
        self.rank = rank
        self.suit = suit
        
    def __str__(self):
        return f"{self.rank}{self.suit.value}"
        
    def __repr__(self):
        return self.__str__()
        
    def get_point_value(self) -> int:
        """获取牌的点数价值"""
        if self.rank in ['A', 'K', 'Q', 'J']:
            return 3
        else:
            return 1

class Player:
    def __init__(self, name: str):
        self.name = name
        self.hand: List[Card] = []
        self.played_cards: List[Card] = []  # 玩家出牌区
        
    def add_cards(self, cards: List[Card]):
        """给玩家添加牌"""
        self.hand.extend(cards)
        
    def remove_cards(self, cards: List[Card]):
        """从玩家手中移除牌"""
        for card in cards:
            if card in self.hand:
                self.hand.remove(card)
                
    def play_cards(self, cards: List[Card]):
        """玩家出牌到出牌区"""
        self.remove_cards(cards)
        self.played_cards.extend(cards)
        
    def clear_played_cards(self):
        """清空玩家出牌区"""
        self.played_cards.clear()
        
    def hand_count(self) -> int:
        """获取手牌数量"""
        return len(self.hand)
        
    def played_count(self) -> int:
        """获取出牌区牌数量"""
        return len(self.played_cards)
        
    def get_score(self) -> int:
        """计算玩家剩余手牌得分"""
        return sum(card.get_point_value() for card in self.hand)
        
    def sort_hand(self):
        """整理手牌，按牌型排序"""
        rank_order = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
                      '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13}
        
        self.hand.sort(key=lambda card: (rank_order[card.rank], card.suit.value))

class GameState(Enum):
    WAITING_FOR_PLAY = "等待出牌"
    WAITING_FOR_CHALLENGE = "等待质疑"
    GAME_OVER = "游戏结束"

class BluffGame:
    # 牌的等级，A可以代替任意牌
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    
    def __init__(self, player_names: List[str]):
        self.players: List[Player] = [Player(name) for name in player_names]
        self.current_player_index = 0
        self.deck: List[Card] = []
        self.community_area: List[Card] = []  # 公共牌区
        self.discard_area: List[Card] = []    # 弃牌区
        self.declared_rank = None  # 当前应该出的牌型
        self.last_player_index = -1  # 最后出牌的玩家
        self.game_state = GameState.WAITING_FOR_PLAY
        self.all_passed = False  # 所有玩家是否都过牌
        self.first_round = True  # 是否为第一轮
        
        # 根据玩家数量确定使用牌数
        if len(self.players) >= 2 and len(self.players) <= 6:
            self.num_decks = 1
        elif len(self.players) >= 7 and len(self.players) <= 10:
            self.num_decks = 2
        else:
            raise ValueError("玩家数量必须在2-10之间")
            
        self._initialize_deck()
        self._deal_cards()
        
        # 确定首位玩家
        self.current_player_index = self._determine_first_player()
        
    def _initialize_deck(self):
        """初始化牌堆"""
        self.deck = []
        for _ in range(self.num_decks):
            for suit in Suit:
                for rank in self.RANKS:
                    self.deck.append(Card(rank, suit))
        random.shuffle(self.deck)
        logger.debug("牌堆初始化完成，共%d张牌", len(self.deck))
        
    def _deal_cards(self):
        """分发手牌"""
        # 平均分发牌
        total_cards = len(self.deck)
        cards_per_player = total_cards // len(self.players)
        
        for i, player in enumerate(self.players):
            player_hand = self.deck[i * cards_per_player:(i + 1) * cards_per_player]
            player.add_cards(player_hand)
            # 整理手牌
            player.sort_hand()
            logger.debug("玩家 %s 获得了 %d 张牌", player.name, len(player_hand))
            
        # 处理多余的牌，放入公共牌区
        remaining_cards = self.deck[cards_per_player * len(self.players):]
        self.community_area.extend(remaining_cards)
        logger.debug("处理完余牌，公共牌区有 %d 张牌", len(remaining_cards))
        
    def _determine_first_player(self) -> int:
        """确定首位玩家"""
        # 第一轮随机选择首位玩家
        first_player = random.randint(0, len(self.players) - 1)
        logger.info("随机选择首位玩家: %s", self.players[first_player].name)
        return first_player
        
    def get_current_player(self) -> Player:
        """获取当前玩家"""
        return self.players[self.current_player_index]
        
    def get_next_player_index(self) -> int:
        """获取下一位玩家索引"""
        return (self.current_player_index + 1) % len(self.players)
        
    def play_cards(self, cards: List[Card], declared_rank: str) -> bool:
        """
        玩家出牌
        返回是否成功出牌
        """
        current_player = self.get_current_player()
        
        # 检查玩家是否有这些牌
        if not all(card in current_player.hand for card in cards):
            logger.warning("玩家 %s 尝试出不拥有的牌", current_player.name)
            return False
            
        # 将玩家出牌区的牌移到公共牌区
        if current_player.played_cards:
            self.community_area.extend(current_player.played_cards)
            logger.debug("将玩家 %s 出牌区的 %d 张牌移到公共牌区", 
                        current_player.name, len(current_player.played_cards))
            current_player.clear_played_cards()
            
        # 玩家出牌到出牌区
        current_player.play_cards(cards)
        self.declared_rank = declared_rank
        self.last_player_index = self.current_player_index
        self.all_passed = False  # 有玩家出牌，重置过牌状态
        self.first_round = False  # 不再是第一轮
        
        logger.info("玩家 %s 出牌: %s，声明为 %s", current_player.name, cards, declared_rank)
        return True
        
    def challenge(self, challenger_index: int, target_player_index: int) -> Tuple[bool, str]:
        """
        玩家质疑
        返回(质疑是否成功, 描述信息)
        """
        challenger = self.players[challenger_index]
        target_player = self.players[target_player_index]
        
        # 检查目标玩家是否有出牌
        if not target_player.played_cards:
            logger.warning("玩家 %s 尝试质疑没有出牌的玩家 %s", 
                          challenger.name, target_player.name)
            return False, "目标玩家没有出牌"
            
        # 验证被质疑玩家的牌
        actual_ranks = [card.rank for card in target_player.played_cards]
        declared_rank = self.declared_rank
        
        # 检查是否符合声明（A可以代替任意牌）
        is_valid = all(rank == declared_rank or rank == 'A' for rank in actual_ranks)
        
        if is_valid:
            # 被质疑玩家牌为真，掀牌者收走所有牌
            challenger.add_cards(self.community_area)
            challenger.add_cards(target_player.played_cards)
            
            logger.info("玩家 %s 质疑失败，%s 的牌是真实的。%s 收走 %d 张公共牌和 %d 张被质疑牌", 
                       challenger.name, target_player.name, challenger.name, 
                       len(self.community_area), len(target_player.played_cards))
            
            self.community_area.clear()
            target_player.clear_played_cards()
            
            # 被质疑玩家变成当前玩家
            self.current_player_index = challenger_index
            
            return True, f"{challenger.name}质疑失败，{target_player.name}的牌是真实的"
        else:
            # 被质疑玩家牌为假，被质疑玩家收回这些牌
            target_player.add_cards(target_player.played_cards)
            logger.info("玩家 %s 质疑成功，%s 的牌是假的。%s 收回自己的牌", 
                       challenger.name, target_player.name, target_player.name)
            target_player.clear_played_cards()
            
            return False, f"{challenger.name}质疑成功，{target_player.name}的牌是假的"
            
    def pass_turn(self, player_index: int) -> str:
        """
        玩家过牌
        返回描述信息
        """
        player = self.players[player_index]
        
        # 检查是否所有玩家都过牌
        # 这里简化实现，实际游戏中需要跟踪所有玩家的选择
        
        # 如果这是本轮第一个过牌的玩家，记录状态
        if not self.all_passed:
            self.all_passed = True
            
        logger.info("玩家 %s 选择过牌", player.name)
        return f"{player.name}选择过牌"
        
    def check_all_passed(self) -> bool:
        """
        检查是否所有玩家都过牌
        """
        # 简化实现：这里假设外部逻辑会调用此函数
        return self.all_passed
        
    def handle_all_passed(self):
        """
        处理所有玩家都过牌的情况
        """
        # 将所有牌移至弃牌区
        total_cards = 0
        for player in self.players:
            if player.played_cards:
                self.discard_area.extend(player.played_cards)
                total_cards += len(player.played_cards)
                player.clear_played_cards()
                
        if self.community_area:
            self.discard_area.extend(self.community_area)
            total_cards += len(self.community_area)
            self.community_area.clear()
            
        logger.info("所有玩家都过牌，共 %d 张牌被移至弃牌区", total_cards)
            
        # 最后出牌的玩家重新开始出牌
        if self.last_player_index != -1:
            self.current_player_index = self.last_player_index
            
        # 重置声明牌型
        next_rank_index = (self.RANKS.index(self.declared_rank) + 1) % len(self.RANKS)
        self.declared_rank = self.RANKS[next_rank_index]
        
    def check_winner(self) -> Optional[Player]:
        """
        检查是否有玩家获胜
        """
        for player in self.players:
            if player.hand_count() == 0:
                # 自动验证最后出的牌
                if player.played_cards:
                    actual_ranks = [card.rank for card in player.played_cards]
                    is_valid = all(rank == self.declared_rank or rank == 'A' 
                                 for rank in actual_ranks)
                    if is_valid:
                        self.game_state = GameState.GAME_OVER
                        logger.info("玩家 %s 获胜！", player.name)
                        return player
        return None
        
    def next_turn(self):
        """进入下一回合"""
        old_player = self.get_current_player()
        self.current_player_index = self.get_next_player_index()
        new_player = self.get_current_player()        
        logger.debug("从玩家 %s 切换到玩家 %s，当前应出牌型: %s", 
                    old_player.name, new_player.name, self.declared_rank)
        
    def display_game_state(self):
        """显示游戏状态"""
        print("\n=== 当前游戏状态 ===")
        print(f"当前玩家: {self.get_current_player().name}")
        print(f"应该出的牌型: {self.declared_rank}")
        print(f"公共牌区: {len(self.community_area)}张牌")
        print(f"弃牌区: {len(self.discard_area)}张牌")
        
        for i, player in enumerate(self.players):
            marker = ">>> " if i == self.current_player_index else "    "
            print(f"{marker}{player.name}: 手牌{player.hand_count()}张, "
                  f"出牌区{player.played_count()}张")
                  
    def get_valid_ranks(self) -> List[str]:
        """获取当前有效的牌型（包括A）"""
        return ['2','3','4','5','6','7','8','9','10','J','Q','K']

def main():
    """主游戏循环"""
    logger.info("唬牌游戏开始")
    
    # 获取玩家数量和姓名
    while True:
        try:
            num_players = int(input("请输入玩家数量 (2-10): "))
            if 2 <= num_players <= 10:
                break
            else:
                print("玩家数量必须在2-10之间")
        except ValueError:
            print("请输入有效的数字")
            
    player_names = []
    for i in range(num_players):
        name = input(f"请输入玩家{i+1}的姓名: ")
        player_names.append(name)
        
    # 创建游戏
    game = BluffGame(player_names)
    
    print("\n游戏开始！")
    print("座位安排:")
    for i, player in enumerate(game.players):
        print(f"  座位{i+1}: {player.name}")
    print(f"第一轮由 {game.get_current_player().name} 先出牌")
    print("规则提示：")
    print("- A可以代替任意牌型")
    print("- 每轮需要按顺序出牌（A,2,3,4,...,K,A,2,...）")
    print("- 你可以选择跟牌、质疑或过牌")
    
    # 游戏主循环
    winner = None
    while game.game_state != GameState.GAME_OVER:
        game.display_game_state()
        current_player = game.get_current_player()
        
        print(f"\n{current_player.name}的回合")
        print(f"你的手牌: {current_player.hand}")
        if game.declared_rank!=None:
            # 获取玩家选择
            print("\n请选择操作:")
            print("1. 跟牌")
            print("2. 质疑")
            print("3. 过牌")
            
            try:
                choice = int(input("请输入选择 (1-3): "))
            except ValueError:
                print("无效输入，请重新选择")
                continue
        else:
            choice = 1
            
        if choice == 1:  # 跟牌
            if not current_player.hand:
                print("你没有手牌了！")
                # 自动进入下一回合
                game.next_turn()
                continue
                
            # 获取要出的牌
            print(f"当前应该出的牌型: {game.declared_rank}")
            print("输入要出的牌的索引（从0开始，用空格分隔）:")
            
            try:
                indices_input = input("例如 '0 2 4' 表示出第1、3、5张牌: ")
                print(f"输入的索引: {indices_input}")
                indices = [int(i) for i in indices_input.split()]
                # 检查索引有效性
                if not all(0 <= i < len(current_player.hand) for i in indices):
                    print("无效的牌索引")
                    continue
                    
                cards_to_play = [current_player.hand[i] for i in indices]
                print(f"选择的牌: {cards_to_play}")
                
                # 获取声明的牌型
                if game.declared_rank is None:
                    declared_rank = input(f"声明牌型 ({game.declared_rank}): ")
                    print(f"声明的牌型: {declared_rank}")
                    if declared_rank not in game.get_valid_ranks():
                        print(f"声明的牌型必须是 {game.get_valid_ranks()}")
                        continue
                    else:
                        game.declared_rank=declared_rank
                    
                # 执行出牌
                if game.play_cards(cards_to_play, game.declared_rank):
                    print(f"成功出牌: {cards_to_play}，声明为 {game.declared_rank}")
                else:
                    print("出牌失败")
                    continue
                    
            except (ValueError, IndexError):
                print("输入格式错误")
                continue
                
        elif choice == 2:  # 质疑
            # 显示有出牌的玩家
            players_with_cards = []
            for i, player in enumerate(game.players):
                if player.played_count() > 0 and i != game.current_player_index:
                    players_with_cards.append((i, player))
                    
            if not players_with_cards:
                print("没有可以质疑的玩家")
                continue
                
            print("可质疑的玩家:")
            for i, (idx, player) in enumerate(players_with_cards):
                print(f"{i+1}. {player.name} (出牌区有{player.played_count()}张牌)")
                
            try:
                target_index = int(input("选择要质疑的玩家编号: ")) - 1
                if 0 <= target_index < len(players_with_cards):
                    target_player_index = players_with_cards[target_index][0]
                    result, message = game.challenge(game.current_player_index, target_player_index)
                    print(message)
                else:
                    print("无效选择")
                    continue
            except ValueError:
                print("输入格式错误")
                continue
                
        elif choice == 3:  # 过牌
            message = game.pass_turn(game.current_player_index)
            print(message)
            
            # 检查是否所有玩家都过牌
            # 这里简化处理，实际应有更复杂的逻辑
            if game.check_all_passed():
                game.handle_all_passed()
                print("所有玩家都过牌，牌堆被清理")
        else:
            print("无效选择")
            continue
            
        # 检查是否有玩家获胜
        winner = game.check_winner()
        if winner:
            print(f"\n恭喜 {winner.name} 获胜！")
            print(f"最终得分: {winner.get_score()} 分")
            game.game_state = GameState.GAME_OVER
            break
            
        # 进入下一回合（质疑不会转移回合，其他操作会）
        if choice != 2:
            game.next_turn()

if __name__ == "__main__":
    main()
