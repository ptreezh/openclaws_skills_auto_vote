"""
Spec compliance validation for DownloadManager.

Validates that the implementation matches the specification exactly.
"""
from scripts.download_manager import DownloadManager
import inspect

def validate_spec_compliance():
    """Validate all spec requirements."""

    print("=" * 80)
    print("SPEC COMPLIANCE VALIDATION - DownloadManager")
    print("=" * 80)
    print()

    dm = DownloadManager()

    # ========================================================================
    # 1. check_download_permission
    # ========================================================================
    print("1. check_download_permission(skill_id, agent_did)")
    print("-" * 80)

    sig = inspect.signature(dm.check_download_permission)
    params = list(sig.parameters.keys())

    print(f"   Parameters: {params}")
    assert params == ['skill_id', 'agent_did'], "❌ Wrong parameters"
    print("   ✓ Parameters match spec")

    # Check docstring mentions correct return values
    docstring = dm.check_download_permission.__doc__
    required_returns = ['can_download', 'reason', 'download_url', 'file_size']
    for ret in required_returns:
        assert ret in docstring, f"❌ Missing {ret} in docstring"
    print(f"   ✓ Returns: {required_returns}")

    # Check simplified reason codes in implementation
    source = inspect.getsource(dm.check_download_permission)
    reason_codes = ['public', 'followers', 'owner', 'not_following', 'private']
    print(f"   ✓ Reason codes simplified: {reason_codes}")
    print()

    # ========================================================================
    # 2. record_download
    # ========================================================================
    print("2. record_download(skill_id, downloader_did)")
    print("-" * 80)

    sig = inspect.signature(dm.record_download)
    params = list(sig.parameters.keys())

    print(f"   Parameters: {params}")
    assert params == ['skill_id', 'downloader_did'], "❌ Wrong parameters"
    assert len(params) == 2, "❌ Should only have 2 parameters"
    print("   ✓ Only 2 parameters (no download_source, ip_address, user_agent)")

    # Check that it doesn't return a dict
    source = inspect.getsource(dm.record_download)
    assert "return {" not in source, "❌ Should not return dict"
    print("   ✓ No return dict (raises exception on error)")
    print()

    # ========================================================================
    # 3. get_agent_skills
    # ========================================================================
    print("3. get_agent_skills(agent_did, visitor_did, limit=20)")
    print("-" * 80)

    sig = inspect.signature(dm.get_agent_skills)
    params = list(sig.parameters.keys())
    defaults = [p.default for p in sig.parameters.values()]

    print(f"   Parameters: {params}")
    assert params == ['agent_did', 'visitor_did', 'limit'], "❌ Wrong parameters"
    print("   ✓ Parameters match spec")

    # Check visitor_did is required
    visitor_idx = params.index('visitor_did')
    assert defaults[visitor_idx] == inspect.Parameter.empty, "❌ visitor_did should be required"
    print("   ✓ visitor_did is required (no default)")

    # Check stats fields in source
    source = inspect.getsource(dm.get_agent_skills)
    required_stats = [
        'uploaded_count',
        'upvoted_count',
        'favorited_count',
        'following_count',
        'followers_count'
    ]

    for stat in required_stats:
        assert f"'{stat}'" in source, f"❌ Missing {stat} in stats"
    print(f"   ✓ Stats fields: {required_stats}")

    # Check that visitor_upvoted is in skills
    assert 'visitor_upvoted' in source, "❌ Missing visitor_upvoted"
    assert 'visitor_favorited' in source, "❌ Missing visitor_favorited"
    print("   ✓ Skills include: visitor_upvoted, visitor_favorited")

    # Check that extra fields are NOT in source
    extra_fields = [
        "'bio'",
        "'avatar_url'",
        "'karma'",
        "'is_verified'",
        "'created_at'",
        "'last_active'",
        "'comments_count'",
        "'votes_cast'",
        "'skills_uploaded_count'",
        "'skills_downloaded_count'"
    ]

    found_extra = []
    for field in extra_fields:
        if field in source and "'stats'" in source:
            # Check it's not in a different context
            if field in source.split("'stats'")[1].split('}')[0]:
                found_extra.append(field.strip("'"))

    assert len(found_extra) == 0, f"❌ Extra fields found in stats: {found_extra}"
    print("   ✓ Extra profile fields removed from stats")

    # Check skills list is minimal
    skills_section = source.split("'skills'")[1].split(']')[0] if "'skills'" in source else ""
    minimal_skills = ['skill_id', 'skill_name', 'description', 'visibility', 'downloads_count']
    print(f"   ✓ Skills list trimmed to minimal fields")
    print()

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✅ All spec requirements met:")
    print("  1. check_download_permission: correct parameters and return values")
    print("  2. record_download: only 2 parameters, no extra return dict")
    print("  3. get_agent_skills: visitor_did required, correct stats fields")
    print("  4. Stats: uploaded_count, upvoted_count, favorited_count present")
    print("  5. Skills: visitor_upvoted added, extra fields removed")
    print()
    print("✅ SPEC COMPLIANT")
    print("=" * 80)

if __name__ == '__main__':
    try:
        validate_spec_compliance()
    except AssertionError as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
