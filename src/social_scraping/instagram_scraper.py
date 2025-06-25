#!/usr/bin/env python3
"""
Instagram Location Scraper
Scrapes Instagram posts by location and time for accident-related content
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

import instaloader
import requests
from instaloader import Instaloader, Post, Profile, exceptions
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.config import Config
from ..utils.logger import StructuredLogger


@dataclass
class InstagramProfile:
    """Instagram profile information"""

    username: str
    full_name: str
    biography: str
    followers: int
    following: int
    posts_count: int
    is_private: bool
    is_verified: bool
    profile_pic_url: str
    external_url: str
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None


@dataclass
class InstagramPost:
    """Instagram post information"""

    shortcode: str
    url: str
    caption: str
    timestamp: datetime
    likes: int
    comments: int
    location_name: str
    location_id: Optional[int]
    owner_username: str
    owner_profile: Optional[InstagramProfile]
    hashtags: List[str]
    mentions: List[str]
    is_video: bool
    media_urls: List[str]


class ProxyRotator:
    """Handles proxy rotation for web scraping"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)
        self.proxies = self._load_proxies()
        self.current_proxy_index = 0
        self.failed_proxies = set()

    def _load_proxies(self) -> List[Dict[str, str]]:
        """Load proxy configuration"""
        if not all(
            [
                self.config.proxy_username,
                self.config.proxy_password,
                self.config.proxy_endpoint,
            ]
        ):
            self.logger.warning(
                "Proxy configuration incomplete, using direct connection"
            )
            return []

        # For BrightData/Storm Proxies, typically multiple endpoints
        proxy_endpoints = [
            f"http://{self.config.proxy_username}:{self.config.proxy_password}@{self.config.proxy_endpoint}"
        ]

        return [{"http": proxy, "https": proxy} for proxy in proxy_endpoints]

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Get next available proxy"""
        if not self.proxies:
            return None

        # Try to find a working proxy
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_proxy_index]
            proxy_key = list(proxy.values())[0]

            if proxy_key not in self.failed_proxies:
                return proxy

            self.current_proxy_index = (self.current_proxy_index + 1) % len(
                self.proxies
            )
            attempts += 1

        # All proxies failed, reset failed set and try again
        self.failed_proxies.clear()
        return self.proxies[0] if self.proxies else None

    def mark_proxy_failed(self, proxy: Dict[str, str]):
        """Mark proxy as failed"""
        if proxy:
            proxy_key = list(proxy.values())[0]
            self.failed_proxies.add(proxy_key)
            self.logger.warning(f"Marked proxy as failed: {proxy_key}")


class InstagramLocationScraper:
    """Scrapes Instagram posts by location for accident-related content"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)
        self.proxy_rotator = ProxyRotator(config)

        # Initialize Instaloader with custom session
        self.loader = Instaloader(
            quiet=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            request_timeout=30,
            max_connection_attempts=3,
        )

        # Configure rate limiting
        self.request_delay = config.request_throttle_seconds
        self.last_request_time = 0

        # Setup requests session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _apply_rate_limiting(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _get_location_by_coordinates(
        self, lat: float, lon: float, radius_km: float = 1.0
    ) -> List[int]:
        """Find Instagram location IDs near given coordinates"""
        try:
            # This would typically use Instagram's location search API
            # For demonstration, we'll use a placeholder implementation

            # In practice, you would:
            # 1. Use Instagram's location search endpoint
            # 2. Search for locations within radius of coordinates
            # 3. Return list of location IDs

            self.logger.info(f"Searching for Instagram locations near {lat}, {lon}")

            # Placeholder: return some example location IDs
            # In real implementation, this would make API calls to find actual locations
            return []

        except Exception as e:
            self.logger.error(f"Error finding Instagram locations: {e}")
            return []

    def scrape_location_posts(
        self, location_id: int, accident_time: datetime, time_window_minutes: int = 30
    ) -> List[InstagramPost]:
        """Scrape Instagram posts from a specific location around accident time"""
        try:
            self._apply_rate_limiting()

            self.logger.info(
                f"Scraping Instagram location {location_id} around {accident_time}"
            )

            # Calculate time window
            start_time = accident_time - timedelta(minutes=time_window_minutes)
            end_time = accident_time + timedelta(minutes=time_window_minutes)

            posts = []

            try:
                # Get location object
                location = self.loader.get_location_by_id(location_id)

                # Iterate through posts at this location
                post_count = 0
                for post in location.get_posts():
                    try:
                        # Check if post is within time window
                        if start_time <= post.date_utc <= end_time:
                            instagram_post = self._extract_post_data(post)
                            if instagram_post:
                                posts.append(instagram_post)
                                post_count += 1

                        # Stop if post is too old
                        elif post.date_utc < start_time:
                            break

                        # Limit number of posts to avoid rate limiting
                        if post_count >= 50:
                            break

                    except Exception as e:
                        self.logger.warning(f"Error processing post: {e}")
                        continue

                self.logger.info(f"Found {len(posts)} posts at location {location_id}")

            except exceptions.InstaloaderException as e:
                self.logger.error(
                    f"Instagram API error for location {location_id}: {e}"
                )

            return posts

        except Exception as e:
            self.logger.error(f"Error scraping location posts: {e}")
            return []

    def _extract_post_data(self, post: Post) -> Optional[InstagramPost]:
        """Extract relevant data from Instagram post"""
        try:
            # Get owner profile information
            owner_profile = None
            try:
                profile = Profile.from_username(
                    self.loader.context, post.owner_username
                )
                owner_profile = self._extract_profile_data(profile)
            except Exception as e:
                self.logger.warning(
                    f"Could not get profile for {post.owner_username}: {e}"
                )

            # Extract hashtags and mentions
            hashtags = (
                [tag for tag in post.caption_hashtags] if post.caption_hashtags else []
            )
            mentions = (
                [mention for mention in post.caption_mentions]
                if post.caption_mentions
                else []
            )

            # Get media URLs
            media_urls = []
            if post.is_video:
                media_urls.append(post.video_url)
            else:
                media_urls.append(post.url)

            # Handle sidecar posts (multiple images)
            if hasattr(post, "get_sidecar_nodes"):
                for node in post.get_sidecar_nodes():
                    if node.is_video:
                        media_urls.append(node.video_url)
                    else:
                        media_urls.append(node.display_url)

            return InstagramPost(
                shortcode=post.shortcode,
                url=f"https://www.instagram.com/p/{post.shortcode}/",
                caption=post.caption or "",
                timestamp=post.date_utc,
                likes=post.likes,
                comments=post.comments,
                location_name=post.location.name if post.location else "",
                location_id=post.location.id if post.location else None,
                owner_username=post.owner_username,
                owner_profile=owner_profile,
                hashtags=hashtags,
                mentions=mentions,
                is_video=post.is_video,
                media_urls=media_urls,
            )

        except Exception as e:
            self.logger.error(f"Error extracting post data: {e}")
            return None

    def _extract_profile_data(self, profile: Profile) -> InstagramProfile:
        """Extract relevant data from Instagram profile"""
        # Extract phone and email from biography
        phone, email = self._extract_contact_info(profile.biography)

        return InstagramProfile(
            username=profile.username,
            full_name=profile.full_name or "",
            biography=profile.biography or "",
            followers=profile.followers,
            following=profile.followees,
            posts_count=profile.mediacount,
            is_private=profile.is_private,
            is_verified=profile.is_verified,
            profile_pic_url=profile.profile_pic_url,
            external_url=profile.external_url or "",
            phone=phone,
            email=email,
            location=self._extract_location_from_bio(profile.biography),
        )

    def _extract_contact_info(
        self, biography: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract phone and email from Instagram biography"""
        import re

        phone = None
        email = None

        if biography:
            # Phone number patterns
            phone_patterns = [
                r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # 123-456-7890
                r"\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b",  # (123) 456-7890
                r"\b\+1\s?\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # +1 123-456-7890
            ]

            for pattern in phone_patterns:
                match = re.search(pattern, biography)
                if match:
                    phone = match.group()
                    break

            # Email pattern
            email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            email_match = re.search(email_pattern, biography)
            if email_match:
                email = email_match.group()

        return phone, email

    def _extract_location_from_bio(self, biography: str) -> Optional[str]:
        """Extract location information from biography"""
        if not biography:
            return None

        # Look for common location indicators
        location_keywords = ["📍", "🌍", "🏠", "located", "based in", "from"]

        for keyword in location_keywords:
            if keyword in biography.lower():
                # Extract text around the keyword
                lines = biography.split("\n")
                for line in lines:
                    if keyword in line.lower():
                        return line.strip()

        return None

    def scrape_accident_location(self, accident_data: Dict) -> List[InstagramPost]:
        """Scrape Instagram posts for a specific accident location and time"""
        try:
            lat = float(accident_data.get("lat", 0))
            lon = float(accident_data.get("lon", 0))
            accident_time = datetime.fromtimestamp(
                accident_data.get("timestamp", 0) / 1000
            )

            self.logger.info(
                f"Scraping Instagram for accident at {lat}, {lon} at {accident_time}"
            )

            # Find Instagram locations near accident coordinates
            location_ids = self._get_location_by_coordinates(lat, lon)

            all_posts = []

            for location_id in location_ids:
                try:
                    posts = self.scrape_location_posts(location_id, accident_time)
                    all_posts.extend(posts)

                    # Add delay between location scraping
                    time.sleep(random.uniform(5, 10))

                except Exception as e:
                    self.logger.error(f"Error scraping location {location_id}: {e}")
                    continue

            # Filter posts for accident-related content
            relevant_posts = self._filter_accident_related_posts(
                all_posts, accident_data
            )

            self.logger.log_data_processing(
                operation="instagram_scraping",
                input_count=len(location_ids),
                output_count=len(relevant_posts),
                processing_time=0,
                accident_id=accident_data.get("id", ""),
                total_posts_found=len(all_posts),
                relevant_posts=len(relevant_posts),
            )

            return relevant_posts

        except Exception as e:
            self.logger.error(f"Error scraping accident location: {e}")
            return []

    def _filter_accident_related_posts(
        self, posts: List[InstagramPost], accident_data: Dict
    ) -> List[InstagramPost]:
        """Filter posts for accident-related content"""
        accident_keywords = [
            "accident",
            "crash",
            "collision",
            "wreck",
            "emergency",
            "police",
            "ambulance",
            "fire truck",
            "traffic",
            "blocked",
            "road closed",
            "incident",
            "emergency services",
        ]

        relevant_posts = []

        for post in posts:
            # Check caption for accident keywords
            caption_lower = post.caption.lower()

            if any(keyword in caption_lower for keyword in accident_keywords):
                relevant_posts.append(post)
                continue

            # Check hashtags
            hashtag_text = " ".join(post.hashtags).lower()
            if any(keyword in hashtag_text for keyword in accident_keywords):
                relevant_posts.append(post)
                continue

        return relevant_posts

    def extract_social_profiles(self, posts: List[InstagramPost]) -> List[Dict]:
        """Extract social profile information from posts"""
        profiles = []

        for post in posts:
            if post.owner_profile and post.owner_profile.phone:
                profile_data = {
                    "platform": "instagram",
                    "username": post.owner_profile.username,
                    "full_name": post.owner_profile.full_name,
                    "phone": post.owner_profile.phone,
                    "email": post.owner_profile.email,
                    "followers": post.owner_profile.followers,
                    "is_verified": post.owner_profile.is_verified,
                    "profile_url": f"https://www.instagram.com/{post.owner_profile.username}/",
                    "post_url": post.url,
                    "post_timestamp": post.timestamp.isoformat(),
                    "relevance_score": self._calculate_relevance_score(post),
                }
                profiles.append(profile_data)

        return profiles

    def _calculate_relevance_score(self, post: InstagramPost) -> float:
        """Calculate relevance score for a post (0-1)"""
        score = 0.0

        # Time proximity (closer to accident time = higher score)
        # This would need accident time to calculate properly
        score += 0.3

        # Engagement (likes + comments)
        engagement = post.likes + post.comments
        if engagement > 100:
            score += 0.3
        elif engagement > 10:
            score += 0.2
        else:
            score += 0.1

        # Profile verification
        if post.owner_profile and post.owner_profile.is_verified:
            score += 0.2

        # Contact information available
        if post.owner_profile and (
            post.owner_profile.phone or post.owner_profile.email
        ):
            score += 0.2

        return min(score, 1.0)

    def close(self):
        """Clean up resources"""
        if hasattr(self, "session"):
            self.session.close()


class InstagramComplianceManager:
    """Manages compliance with Instagram's terms and privacy regulations"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)

    def check_robots_txt(self, url: str) -> bool:
        """Check if scraping is allowed by robots.txt"""
        try:
            robots_url = f"{url}/robots.txt"
            response = requests.get(robots_url, timeout=10)

            if response.status_code == 200:
                # Parse robots.txt for scraping restrictions
                # This is a simplified check
                content = response.text.lower()
                if "disallow: /" in content:
                    self.logger.warning(f"Robots.txt disallows scraping for {url}")
                    return False

            return True

        except Exception as e:
            self.logger.warning(f"Could not check robots.txt for {url}: {e}")
            return True  # Allow by default if can't check

    def generate_opt_out_link(self, profile_data: Dict) -> str:
        """Generate opt-out link for GDPR/CCPA compliance"""
        base_url = self.config.opt_out_webhook_url
        if not base_url:
            return ""

        # Create opt-out URL with profile identifier
        opt_out_url = (
            f"{base_url}?platform=instagram&username={profile_data.get('username', '')}"
        )
        return opt_out_url

    def should_exclude_profile(self, profile: InstagramProfile) -> bool:
        """Check if profile should be excluded (protected classes)"""
        # Exclude verified accounts that might be public figures
        if profile.is_verified:
            return True

        # Exclude accounts with government/emergency service indicators
        bio_lower = profile.biography.lower()
        protected_keywords = [
            "police",
            "fire department",
            "ems",
            "paramedic",
            "government",
            "official",
            "public safety",
            "first responder",
            "emergency services",
        ]

        if any(keyword in bio_lower for keyword in protected_keywords):
            return True

        return False
