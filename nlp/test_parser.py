# test_parser.py
import json
import sys
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
sys.path.append(str(Path(__file__).parent.parent))

# Use rule-based parser (no API needed)
from nlp.cv_parser import parse_cv

cv_file_path = "/Users/serenamendanha/Desktop/Resume_general.pdf"
preferences_text = "Looking for software engineering roles in Dublin"

print(f"\n📄 Parsing CV: {cv_file_path}")
print(f"💼 Preferences: {preferences_text}")
print(f"🤖 Using Rule-based Parser (No API required)")
print("-" * 60)

try:
    if not Path(cv_file_path).exists():
        print(f"✗ File not found: {cv_file_path}")
        sys.exit(1)
    
    print(f"✓ File exists ({Path(cv_file_path).stat().st_size:,} bytes)")
    
    print("\n🔄 Running CV parser...")
    start_time = datetime.now()
    profile = parse_cv(cv_file_path, preferences_text)
    end_time = datetime.now()
    
    print(f"✓ Parsing completed in {(end_time - start_time).total_seconds():.2f} seconds")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 PARSING SUMMARY:")
    print("="*60)
    
    print(f"\n👤 Name: {profile.get('name', 'Not found')}")
    print(f"📧 Email: {profile.get('email', 'Not found')}")
    print(f"📱 Phone: {profile.get('phone', 'Not found')}")
    print(f"🔗 LinkedIn: {profile.get('linkedin', 'Not found')}")
    print(f"💻 GitHub: {profile.get('github', 'Not found')}")
    
    print(f"\n🎯 Skills ({len(profile.get('skills', []))}):")
    if profile.get('skills'):
        print(f"   {', '.join(profile['skills'][:15])}")
    
    print(f"\n💼 Job Titles ({len(profile.get('job_titles', []))}):")
    for title in profile.get('job_titles', []):
        print(f"   • {title}")
    
    print(f"\n⏰ Work Experience ({profile.get('years_experience', 0)} years total):")
    for exp in profile.get('experiences', []):
        print(f"   • {exp.get('role')} at {exp.get('company')}")
        print(f"     {exp.get('start_month', '?')}/{exp.get('start_year')} - {exp.get('end_month', '?')}/{exp.get('end_year')}")
    
    print(f"\n📈 Seniority: {profile.get('seniority_level')}")
    print(f"🎯 Target Role: {profile.get('target_role')}")
    print(f"📍 Target Location: {profile.get('target_location')}")
    
    # Save to file
    with open('parsed_profile.json', 'w') as f:
        json.dump(profile, f, indent=2, default=str)
    print(f"\n💾 Profile saved to parsed_profile.json")
    
    print("\n✨ Parsing completed successfully!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()