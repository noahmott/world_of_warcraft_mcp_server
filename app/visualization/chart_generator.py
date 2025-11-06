"""
Chart and Visualization Generator
"""

import io
import base64
import logging
import os
import uuid
from typing import Dict, Any, List, Optional
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.graph_objects as go  # type: ignore[import-untyped]
import plotly.io as pio  # type: ignore[import-untyped]

from ..utils.wow_utils import get_localized_name, parse_class_info
from ..utils.image_storage import image_storage

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generate charts and visualizations for WoW guild analysis"""
    
    def __init__(self):
        # Set default theme
        plt.style.use('dark_background')
        sns.set_theme(style="darkgrid")
        
        # Set figure DPI for better quality
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['savefig.dpi'] = 100
        
        # WoW class colors for consistency
        self.class_colors = {
            "Death Knight": "#C41E3A",
            "Demon Hunter": "#A330C9",
            "Druid": "#FF7C0A",
            "Evoker": "#33937F",
            "Hunter": "#AAD372",
            "Mage": "#3FC7EB",
            "Monk": "#00FF98",
            "Paladin": "#F48CBA",
            "Priest": "#FFFFFF",
            "Rogue": "#FFF468",
            "Shaman": "#0070DD",
            "Warlock": "#8788EE",
            "Warrior": "#C69B6D"
        }
        
        # Difficulty colors
        self.difficulty_colors = {
            "LFR": "#71D5FF",
            "Normal": "#1EFF00",
            "Heroic": "#0070DD",
            "Mythic": "#FF8000"
        }
    
    async def create_raid_progress_chart(self, guild_data: Dict[str, Any], raid_tier: str = "current", guild_name: Optional[str] = None) -> str:
        """
        Create interactive raid progression chart using Plotly

        Args:
            guild_data: Guild data from Blizzard API
            raid_tier: Raid tier to analyze
            guild_name: Optional guild name for filename

        Returns:
            Public URL to interactive HTML chart
        """
        try:
            # Extract guild achievements for raid progress
            achievements = guild_data.get("guild_achievements", {})
            guild_info = guild_data.get("guild_info", {})

            # Extract raid progress data
            raid_data = self._extract_raid_progress(achievements, raid_tier)

            if not raid_data:
                return await self._create_no_data_chart("No raid progression data available")

            # Create Plotly figure with subplots
            from plotly.subplots import make_subplots

            fig = make_subplots(
                rows=len(raid_data),
                cols=1,
                subplot_titles=[f"{raid['name']} - {raid['tier']}" for raid in raid_data],
                vertical_spacing=0.15
            )

            guild_display_name = guild_name or get_localized_name(guild_info)

            for i, raid in enumerate(raid_data, 1):
                difficulties = raid.get("difficulties", [])

                if difficulties:
                    x_labels = [d["difficulty"] for d in difficulties]
                    y_values = [d["bosses_killed"] for d in difficulties]
                    max_bosses = [d["total_bosses"] for d in difficulties]
                    colors = [self.difficulty_colors.get(d, "#CCCCCC") for d in x_labels]

                    # Add bar chart
                    fig.add_trace(
                        go.Bar(
                            x=x_labels,
                            y=y_values,
                            marker_color=colors,
                            text=[f"{killed}/{total}" for killed, total in zip(y_values, max_bosses)],
                            textposition='outside',
                            name=raid['name'],
                            hovertemplate='<b>%{x}</b><br>Bosses Killed: %{y}<br><extra></extra>',
                            showlegend=False
                        ),
                        row=i, col=1
                    )

                    # Add max boss reference lines
                    for x_idx, max_boss in enumerate(max_bosses):
                        fig.add_hline(
                            y=max_boss,
                            line_dash="dash",
                            line_color="red",
                            opacity=0.5,
                            row=i, col=1
                        )

            # Update layout
            fig.update_layout(
                title={
                    "text": f"Raid Progression - {guild_display_name}",
                    "x": 0.5,
                    "xanchor": "center",
                    "font": {"size": 24, "color": "white"}
                },
                template="plotly_dark",
                height=400 * len(raid_data),
                showlegend=False,
                font={"color": "white"}
            )

            # Update y-axes
            fig.update_yaxes(title_text="Bosses Killed", color="white")

            # Generate HTML
            html_content = pio.to_html(fig, include_plotlyjs='cdn', full_html=True)

            # Upload to Supabase and return URL with unique identifier
            safe_name = guild_name.lower().replace(' ', '-').replace("'", '') if guild_name else 'guild'
            unique_id = uuid.uuid4().hex[:8]
            url = await image_storage.upload_html(
                html_content,
                filename=f"raid_progress_{safe_name}_{unique_id}.html"
            )

            if url:
                logger.info(f"Generated interactive raid progress chart for {len(raid_data)} raids: {url}")
                return url
            else:
                return "Error: Failed to upload chart to storage"

        except Exception as e:
            logger.error(f"Error creating raid progress chart: {str(e)}")
            return await self._create_error_chart(f"Error generating chart: {str(e)}")
    
    async def create_member_comparison_chart(self, member_data: List[Dict[str, Any]], metric: str) -> str:
        """
        Create member comparison chart
        
        Args:
            member_data: List of member data
            metric: Metric to compare
        
        Returns:
            Base64 encoded PNG image
        """
        try:
            if not member_data:
                return await self._create_no_data_chart("No member data available for comparison")
            
            # Extract data for comparison
            names = []
            values = []
            classes = []
            colors = []
            
            for member in member_data:
                name = get_localized_name(member)
                names.append(name)
                
                # Extract metric value
                if metric == "item_level":
                    value = member.get("equipment_summary", {}).get("average_item_level", 0)
                elif metric == "achievement_points":
                    value = member.get("achievement_points", 0)
                elif metric == "level":
                    value = member.get("level", 0)
                elif metric == "guild_rank":
                    value = member.get("guild_rank", 999)
                else:
                    value = 0
                
                values.append(value)
                
                # Get class for coloring
                class_name = parse_class_info(member.get("character_class"))
                classes.append(class_name)
                colors.append(self.class_colors.get(class_name, "#CCCCCC"))
            
            # Create figure
            fig_width = max(8, len(names) * 0.8)
            fig, ax = plt.subplots(figsize=(fig_width, 6))
            
            # Create bar chart
            bars = ax.bar(names, values, color=colors)
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                label = f"{value:.1f}" if isinstance(value, float) else str(value)
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       label, ha='center', va='bottom', color='white')
            
            # Customize plot
            ax.set_title(f"Member Comparison - {metric.replace('_', ' ').title()}", 
                        fontsize=16, color='white', pad=20)
            ax.set_xlabel('Member Name', color='white')
            ax.set_ylabel(metric.replace('_', ' ').title(), color='white')
            ax.tick_params(colors='white')
            plt.xticks(rotation=45, ha='right')
            
            # Add grid for better readability
            ax.grid(True, axis='y', alpha=0.3)
            
            plt.tight_layout()
            
            # Generate image bytes
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', facecolor='#1a1a1a', edgecolor='none', bbox_inches='tight')
            plt.close()
            buffer.seek(0)
            img_bytes = buffer.read()

            # Upload to Supabase and return URL
            url = await image_storage.upload_chart(img_bytes, filename=f"member_comparison_{metric}.png")
            if url:
                logger.info(f"Generated member comparison chart for {len(member_data)} members: {url}")
                return url
            else:
                return "Error: Failed to upload chart to storage"
            
        except Exception as e:
            logger.error(f"Error creating member comparison chart: {str(e)}")
            return await self._create_error_chart(f"Error generating chart: {str(e)}")
    
    async def create_class_distribution_chart(self, member_data: List[Dict[str, Any]]) -> str:
        """
        Create class distribution pie chart
        
        Args:
            member_data: List of member data
        
        Returns:
            Base64 encoded PNG image
        """
        try:
            if not member_data:
                return await self._create_no_data_chart("No member data available")
            
            # Count classes
            class_counts: Dict[str, int] = {}
            for member in member_data:
                class_name = parse_class_info(member.get("character_class"))
                class_counts[class_name] = class_counts.get(class_name, 0) + 1
            
            # Create pie chart
            fig = go.Figure()
            
            fig.add_trace(go.Pie(
                labels=list(class_counts.keys()),
                values=list(class_counts.values()),
                marker_colors=[self.class_colors.get(cls, "#CCCCCC") for cls in class_counts.keys()],
                textinfo="label+percent+value",
                textposition="auto",
                hovertemplate="<b>%{label}</b><br>" +
                             "Count: %{value}<br>" +
                             "Percentage: %{percent}<extra></extra>"
            ))
            
            # Update layout
            fig.update_layout(
                title={
                    "text": "Guild Class Distribution",
                    "x": 0.5,
                    "font": {"size": 20, "color": "white"}
                },
                template="plotly_dark",
                width=800,
                height=600,
                font={"color": "white"}
            )
            
            # Generate image bytes
            img_bytes = pio.to_image(fig, format="png", width=800, height=600)

            # Upload to Supabase and return URL
            url = await image_storage.upload_chart(img_bytes, filename=f"class_distribution.png")
            if url:
                logger.info(f"Generated class distribution chart for {len(class_counts)} classes: {url}")
                return url
            else:
                return "Error: Failed to upload chart to storage"
            
        except Exception as e:
            logger.error(f"Error creating class distribution chart: {str(e)}")
            return await self._create_error_chart(f"Error generating chart: {str(e)}")
    
    async def create_level_distribution_chart(self, member_data: List[Dict[str, Any]]) -> str:
        """
        Create level distribution histogram
        
        Args:
            member_data: List of member data
        
        Returns:
            Base64 encoded PNG image
        """
        try:
            if not member_data:
                return await self._create_no_data_chart("No member data available")
            
            # Extract levels
            levels = [member.get("level", 0) for member in member_data]
            
            # Create histogram
            fig = go.Figure()
            
            fig.add_trace(go.Histogram(
                x=levels,
                nbinsx=20,
                marker_color="#3FC7EB",
                opacity=0.7,
                hovertemplate="Level Range: %{x}<br>" +
                             "Member Count: %{y}<extra></extra>"
            ))
            
            # Update layout
            fig.update_layout(
                title={
                    "text": "Guild Level Distribution",
                    "x": 0.5,
                    "font": {"size": 20, "color": "white"}
                },
                xaxis_title="Character Level",
                yaxis_title="Number of Members",
                template="plotly_dark",
                width=800,
                height=600,
                font={"color": "white"}
            )
            
            # Generate image bytes
            img_bytes = pio.to_image(fig, format="png", width=800, height=600)

            # Upload to Supabase and return URL
            url = await image_storage.upload_chart(img_bytes, filename=f"level_distribution.png")
            if url:
                logger.info(f"Generated level distribution chart for {len(member_data)} members: {url}")
                return url
            else:
                return "Error: Failed to upload chart to storage"
            
        except Exception as e:
            logger.error(f"Error creating level distribution chart: {str(e)}")
            return await self._create_error_chart(f"Error generating chart: {str(e)}")
    
    def _extract_raid_progress(self, achievements: Dict[str, Any], raid_tier: str) -> List[Dict[str, Any]]:
        """Extract raid progress from achievement data"""
        # Map of raid tiers to their achievements
        RAID_ACHIEVEMENT_MAP = {
            "current": {
                "Nerub-ar Palace": {
                    "tier": "The War Within",
                    "achievements": {"Guild Run": 40256, "Heroic": 40257, "Mythic": 40258}
                }
            },
            "war-within": {
                "Nerub-ar Palace": {
                    "tier": "The War Within",
                    "achievements": {"Guild Run": 40256, "Heroic": 40257, "Mythic": 40258}
                }
            },
            "dragonflight": {
                "Amirdrassil, the Dream's Hope": {
                    "tier": "Dragonflight S3",
                    "achievements": {"LFR": 19320, "Normal": 19331, "Heroic": 19332, "Mythic": 19333}
                },
                "Aberrus, the Shadowed Crucible": {
                    "tier": "Dragonflight S2",
                    "achievements": {"LFR": 18151, "Normal": 18160, "Heroic": 18161, "Mythic": 18162}
                },
                "Vault of the Incarnates": {
                    "tier": "Dragonflight S1",
                    "achievements": {"LFR": 16335, "Normal": 16343, "Heroic": 16345, "Mythic": 16346}
                }
            },
            "shadowlands": {
                "Sepulcher of the First Ones": {
                    "tier": "Shadowlands S4",
                    "achievements": {"LFR": 15416, "Normal": 15417, "Heroic": 15418, "Mythic": 15419}
                },
                "Sanctum of Domination": {
                    "tier": "Shadowlands S2",
                    "achievements": {"LFR": 15126, "Normal": 15134, "Heroic": 15135, "Mythic": 15136}
                },
                "Castle Nathria": {
                    "tier": "Shadowlands S1",
                    "achievements": {"LFR": 14715, "Normal": 14717, "Heroic": 14718, "Mythic": 14719}
                }
            },
            "bfa": {
                "The Eternal Palace": {
                    "tier": "Battle for Azeroth",
                    "achievements": {"Guild Run": 13734}
                }
            },
            "legion": {
                "Vault of the Wardens": {
                    "tier": "Legion",
                    "achievements": {"Mythic Guild Run": 10861}
                }
            },
            "wod": {
                "Draenor Raids": {
                    "tier": "Warlords of Draenor",
                    "achievements": {"Glory": 9669}
                }
            },
            "mop": {
                "Mogu'shan Vaults": {
                    "tier": "Mists of Pandaria",
                    "achievements": {"Guild Run": 6668}
                },
                "Mogu'shan Palace": {
                    "tier": "Mists of Pandaria",
                    "achievements": {"Heroic Guild Run": 6766}
                },
                "Pandaria Raids": {
                    "tier": "Mists of Pandaria",
                    "achievements": {"Glory": 6682}
                }
            },
            "cataclysm": {
                "Cataclysm Raids": {
                    "tier": "Cataclysm",
                    "achievements": {"Glory": 4988}
                }
            }
        }

        # Get raids for the requested tier
        raids_to_check = RAID_ACHIEVEMENT_MAP.get(raid_tier.lower(), RAID_ACHIEVEMENT_MAP.get("current", {}))

        raid_progress = []
        achievement_list = achievements.get("achievements", [])

        for raid_name, raid_info in raids_to_check.items():
            raid_difficulties = []

            for difficulty, ach_id in raid_info["achievements"].items():
                # Find this achievement in the guild's achievements
                for ach in achievement_list:
                    if ach.get("id") == ach_id:
                        # Check completion status
                        criteria = ach.get("criteria", {})
                        completed = criteria.get("is_completed", False)

                        # Count bosses from child criteria
                        child_criteria = criteria.get("child_criteria", [])
                        bosses_killed = sum(1 for child in child_criteria if child.get("is_completed", False))
                        total_bosses = len(child_criteria) if child_criteria else 0

                        # If no child criteria but achievement is complete, assume full clear
                        if total_bosses == 0 and completed:
                            # Estimate boss counts for raids
                            boss_estimates = {
                                "Nerub-ar Palace": 8,
                                "Amirdrassil, the Dream's Hope": 9,
                                "Aberrus, the Shadowed Crucible": 9,
                                "Vault of the Incarnates": 8,
                                "Sepulcher of the First Ones": 11,
                                "Sanctum of Domination": 10,
                                "Castle Nathria": 10
                            }
                            total_bosses = boss_estimates.get(raid_name, 8)
                            bosses_killed = total_bosses

                        raid_difficulties.append({
                            "difficulty": difficulty,
                            "bosses_killed": bosses_killed,
                            "total_bosses": total_bosses
                        })
                        break

            # Only add raid if we found any progress
            if raid_difficulties:
                raid_progress.append({
                    "name": raid_name,
                    "tier": raid_info["tier"],
                    "difficulties": raid_difficulties
                })

        return raid_progress
    
    async def _create_no_data_chart(self, message: str) -> str:
        """Create a chart indicating no data available"""
        fig, ax = plt.subplots(figsize=(8, 4))
        
        ax.text(0.5, 0.5, message,
               ha='center', va='center', transform=ax.transAxes,
               fontsize=20, color='white')
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # Generate image bytes
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', facecolor='#1a1a1a', edgecolor='none', bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        img_bytes = buffer.read()

        # Upload to Supabase and return URL
        url = await image_storage.upload_chart(img_bytes, filename=f"no_data.png")
        return url if url else "Error: No data available and failed to upload error chart"

    async def _create_error_chart(self, error_message: str) -> str:
        """Create a chart indicating an error occurred"""
        fig, ax = plt.subplots(figsize=(8, 4))

        ax.text(0.5, 0.5, f"Error: {error_message}",
               ha='center', va='center', transform=ax.transAxes,
               fontsize=16, color='red')

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Generate image bytes
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', facecolor='#1a1a1a', edgecolor='none', bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        img_bytes = buffer.read()

        # Upload to Supabase and return URL
        url = await image_storage.upload_chart(img_bytes, filename=f"error.png")
        return url if url else f"Error: {error_message} (and failed to upload error chart)"