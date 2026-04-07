/**
 * 출발/도착 검색 바 + Kakao Places 자동완성.
 */

// TODO: Phase 4에서 구현
// - 출발지, 도착지 input 2개
// - Kakao Places API로 자동완성
// - 검색 버튼 → /routes 페이지로 이동 (좌표 전달)

export default function SearchBar() {
  return (
    <div>
      <input placeholder="출발지" />
      <input placeholder="도착지" />
      <button>경로 검색</button>
    </div>
  );
}
