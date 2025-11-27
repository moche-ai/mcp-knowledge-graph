"""Knowledge Graph 3D Viewer - 시각화 페이지 및 데이터 API."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os

router = APIRouter()

# Neo4j 연결 설정
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

async def get_neo4j_session():
    """Neo4j 세션 생성."""
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        return driver
    except Exception as e:
        print(f"Neo4j connection error: {e}")
        return None


@router.get("/graph-data")
async def get_graph_data():
    """그래프 시각화용 노드/링크 데이터 반환."""
    driver = await get_neo4j_session()
    if not driver:
        return {"nodes": [], "links": []}
    
    try:
        async with driver.session() as session:
            # 노드 가져오기
            nodes_result = await session.run("""
                MATCH (e:Entity)
                RETURN 
                    e.id as id,
                    e.name as name,
                    e.entity_type as type,
                    e.description as description,
                    e.trust_score as trust_score,
                    e.properties as properties
                LIMIT 500
            """)
            nodes = []
            async for record in nodes_result:
                node_data = {
                    "id": record["id"] or record["name"],
                    "name": record["name"],
                    "type": record["type"] or "unknown",
                    "description": record["description"] or "",
                    "trust_score": record["trust_score"] or 0.5,
                }
                # properties가 있으면 추가
                if record["properties"]:
                    try:
                        import json
                        props = json.loads(record["properties"]) if isinstance(record["properties"], str) else record["properties"]
                        node_data["properties"] = props
                    except:
                        pass
                nodes.append(node_data)
            
            # 관계 가져오기
            links_result = await session.run("""
                MATCH (a:Entity)-[r]->(b:Entity)
                RETURN 
                    a.id as source_id,
                    a.name as source_name,
                    b.id as target_id,
                    b.name as target_name,
                    type(r) as relation_type
                LIMIT 1000
            """)
            links = []
            async for record in links_result:
                links.append({
                    "source": record["source_id"] or record["source_name"],
                    "target": record["target_id"] or record["target_name"],
                    "type": record["relation_type"],
                })
            
            return {"nodes": nodes, "links": links}
    except Exception as e:
        print(f"Graph data error: {e}")
        return {"nodes": [], "links": []}
    finally:
        await driver.close()


VIEWER_HTML = r"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🧠 Knowledge Graph Viewer</title>
    <script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>
    <script src="https://unpkg.com/3d-force-graph@1.73.0/dist/3d-force-graph.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            overflow: hidden;
            touch-action: manipulation;
        }
        #graph { width: 100vw; height: 100vh; }
        
        .panel {
            position: fixed;
            background: rgba(15, 15, 25, 0.95);
            border: 1px solid rgba(100, 100, 140, 0.3);
            border-radius: 12px;
            backdrop-filter: blur(10px);
            z-index: 100;
            transition: all 0.3s ease;
            overflow: hidden;
        }
        
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            cursor: pointer;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
        }
        
        .panel-header:hover {
            background: rgba(100, 100, 140, 0.1);
        }
        
        .panel-header h3 {
            margin: 0;
            font-size: 14px;
            font-weight: 600;
            color: #a0a0ff;
        }
        
        .collapse-btn {
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(100, 100, 140, 0.2);
            border-radius: 6px;
            font-size: 12px;
            transition: transform 0.3s ease;
        }
        
        .panel.collapsed .collapse-btn {
            transform: rotate(180deg);
        }
        
        .panel-content {
            padding: 0 16px 16px;
            max-height: 300px;
            overflow-y: auto;
            transition: max-height 0.3s ease, padding 0.3s ease, opacity 0.3s ease;
        }
        
        .panel.collapsed .panel-content {
            max-height: 0;
            padding: 0 16px;
            opacity: 0;
        }
        
        .stats-panel {
            top: 70px;
            left: 10px;
            min-width: 180px;
        }
        
        .legend-panel {
            top: 70px;
            right: 10px;
            min-width: 160px;
            max-width: 200px;
        }
        
        .info-panel {
            bottom: 10px;
            left: 10px;
            right: 10px;
            max-height: 250px;
            display: none;
        }
        
        .info-panel.active { display: block; }
        
        .info-panel .close-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 100, 100, 0.2);
            border-radius: 50%;
            cursor: pointer;
            font-size: 14px;
        }
        
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid rgba(100, 100, 140, 0.2);
            font-size: 13px;
        }
        
        .stat-value { color: #60d060; font-weight: 600; }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px 0;
            font-size: 11px;
        }
        
        .legend-color {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        
        .legend-text {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .search-box {
            position: fixed;
            top: 10px;
            left: 10px;
            right: 10px;
            z-index: 100;
        }
        
        .search-box input {
            padding: 12px 20px;
            width: 100%;
            max-width: 400px;
            border: 1px solid rgba(100, 100, 140, 0.4);
            border-radius: 25px;
            background: rgba(15, 15, 25, 0.95);
            color: #fff;
            font-size: 14px;
            outline: none;
        }
        
        .search-box input:focus {
            border-color: #6060ff;
        }
        
        .node-info {
            padding: 16px;
            padding-right: 40px;
        }
        
        .node-info h4 {
            color: #80c0ff;
            margin-bottom: 8px;
            font-size: 16px;
        }
        
        .node-info p {
            font-size: 13px;
            line-height: 1.6;
            color: #b0b0b0;
            margin-bottom: 6px;
        }
        
        .node-info .tag {
            display: inline-block;
            padding: 2px 8px;
            background: rgba(100, 100, 255, 0.2);
            border-radius: 4px;
            font-size: 11px;
            margin-right: 6px;
            margin-bottom: 4px;
        }
        
        /* 모바일 토글 버튼 */
        .mobile-toggle {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            background: rgba(100, 100, 255, 0.9);
            border-radius: 50%;
            display: none;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            z-index: 150;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        
        /* 데스크탑 */
        @media (min-width: 769px) {
            .search-box {
                left: 50%;
                right: auto;
                transform: translateX(-50%);
            }
            
            .stats-panel {
                top: 20px;
                left: 20px;
                min-width: 200px;
            }
            
            .legend-panel {
                top: 20px;
                right: 20px;
                min-width: 180px;
                max-width: 250px;
            }
            
            .info-panel {
                bottom: 20px;
                left: 20px;
                right: 20px;
            }
        }
        
        /* 모바일 */
        @media (max-width: 768px) {
            .stats-panel, .legend-panel {
                left: 10px;
                right: 10px;
                min-width: auto;
                max-width: none;
            }
            
            .stats-panel {
                top: 70px;
            }
            
            .legend-panel {
                top: auto;
                bottom: 80px;
            }
            
            .stats-panel.collapsed,
            .legend-panel.collapsed {
                width: auto;
            }
            
            .mobile-toggle {
                display: flex;
            }
            
            .legend-panel .panel-content {
                max-height: 150px;
            }
            
            .info-panel {
                bottom: 70px;
                max-height: 180px;
            }
            
            /* 모바일에서 기본 접힌 상태 */
            .panel.mobile-default-collapsed .panel-content {
                max-height: 0;
                padding: 0 16px;
                opacity: 0;
            }
            
            .panel.mobile-default-collapsed .collapse-btn {
                transform: rotate(180deg);
            }
        }
        
        /* 매우 작은 화면 */
        @media (max-width: 400px) {
            .search-box input {
                padding: 10px 16px;
                font-size: 13px;
            }
            
            .panel-header {
                padding: 10px 12px;
            }
            
            .panel-content {
                padding: 0 12px 12px;
            }
            
            .stat-row, .legend-item {
                font-size: 11px;
            }
        }
    </style>
</head>
<body>
    <div id="graph"></div>
    
    <div class="search-box">
        <input type="text" id="search" placeholder="🔍 검색어 입력..." />
    </div>
    
    <div class="panel stats-panel" id="stats-panel">
        <div class="panel-header" id="stats-header">
            <h3>📊 통계</h3>
            <div class="collapse-btn">▼</div>
        </div>
        <div class="panel-content">
            <div class="stat-row">
                <span>총 노드</span>
                <span class="stat-value" id="node-count">0</span>
            </div>
            <div class="stat-row">
                <span>총 링크</span>
                <span class="stat-value" id="link-count">0</span>
            </div>
            <div class="stat-row">
                <span>카테고리</span>
                <span class="stat-value" id="type-count">0</span>
            </div>
        </div>
    </div>
    
    <div class="panel legend-panel" id="legend-panel">
        <div class="panel-header" id="legend-header">
            <h3>🎨 범례</h3>
            <div class="collapse-btn">▼</div>
        </div>
        <div class="panel-content">
            <div id="legend"></div>
        </div>
    </div>
    
    <div class="panel info-panel" id="info-panel">
        <div class="close-btn" id="info-close-btn">✕</div>
        <div class="node-info" id="node-info"></div>
    </div>
    
    <div class="mobile-toggle" id="mobile-toggle-btn">☰</div>

    <script>
        const TYPE_COLORS = {
            technology: '#00d4ff',
            framework: '#00b4d8',
            model: '#48cae4',
            service: '#90e0ef',
            tool: '#ade8f4',
            project: '#0096c7',
            concept: '#ff6b6b',
            topic: '#ff8fa3',
            fact: '#ffb3c1',
            news: '#ffd93d',
            article: '#ffea00',
            document: '#95a5a6',
            person: '#6bcb77',
            organization: '#4d96ff',
            cryptocurrency: '#f9ca24',
            stock: '#fdcb6e',
            asset: '#f0932b',
            etf: '#e17055',
            event: '#a29bfe',
            location: '#74b9ff',
            product: '#fd79a8',
            unknown: '#7f8c8d'
        };
        
        let graphData = { nodes: [], links: [] };
        let Graph;
        let allPanelsCollapsed = false;
        
        // 패널 토글 함수
        function togglePanel(panelId) {
            const panel = document.getElementById(panelId);
            panel.classList.toggle('collapsed');
            
            // localStorage에 상태 저장
            const isCollapsed = panel.classList.contains('collapsed');
            localStorage.setItem(`panel_${panelId}`, isCollapsed ? 'collapsed' : 'expanded');
        }
        
        // 모든 패널 토글 (모바일용)
        function toggleAllPanels() {
            allPanelsCollapsed = !allPanelsCollapsed;
            const panels = ['stats-panel', 'legend-panel'];
            panels.forEach(id => {
                const panel = document.getElementById(id);
                if (allPanelsCollapsed) {
                    panel.classList.add('collapsed');
                } else {
                    panel.classList.remove('collapsed');
                }
            });
            
            // 토글 버튼 아이콘 변경
            const toggleBtn = document.querySelector('.mobile-toggle');
            toggleBtn.textContent = allPanelsCollapsed ? '📊' : '☰';
        }
        
        // 정보 패널 닫기
        function closeInfoPanel() {
            document.getElementById('info-panel').classList.remove('active');
        }
        
        // 패널 상태 복원
        function restorePanelStates() {
            const isMobile = window.innerWidth <= 768;
            const panels = ['stats-panel', 'legend-panel'];
            
            panels.forEach(id => {
                const panel = document.getElementById(id);
                const savedState = localStorage.getItem(`panel_${id}`);
                
                if (isMobile && !savedState) {
                    // 모바일에서 처음 방문 시 기본 접힌 상태
                    panel.classList.add('collapsed');
                } else if (savedState === 'collapsed') {
                    panel.classList.add('collapsed');
                }
            });
        }
        
        async function loadData() {
            try {
                const response = await fetch('/knowledge/graph-data');
                graphData = await response.json();
                
                // 통계 업데이트
                document.getElementById('node-count').textContent = graphData.nodes.length;
                document.getElementById('link-count').textContent = graphData.links.length;
                
                const types = [...new Set(graphData.nodes.map(n => n.type))].sort();
                document.getElementById('type-count').textContent = types.length;
                
                // 범례 생성 (개수 순으로 정렬)
                const typeCounts = {};
                types.forEach(type => {
                    typeCounts[type] = graphData.nodes.filter(n => n.type === type).length;
                });
                
                const sortedTypes = types.sort((a, b) => typeCounts[b] - typeCounts[a]);
                
                const legendEl = document.getElementById('legend');
                legendEl.innerHTML = sortedTypes.map(type => `
                    <div class="legend-item" onclick="filterByType('${type}')">
                        <div class="legend-color" style="background: ${TYPE_COLORS[type] || '#7f8c8d'}"></div>
                        <span class="legend-text">${type} (${typeCounts[type]})</span>
                    </div>
                `).join('');
                
                renderGraph();
            } catch (error) {
                console.error('데이터 로드 실패:', error);
            }
        }
        
        // 타입별 필터링
        function filterByType(type) {
            const filteredNodes = graphData.nodes.filter(n => n.type === type);
            const nodeIds = new Set(filteredNodes.map(n => n.id));
            const filteredLinks = graphData.links.filter(l => 
                nodeIds.has(l.source.id || l.source) && nodeIds.has(l.target.id || l.target)
            );
            
            Graph.graphData({ nodes: filteredNodes, links: filteredLinks });
            
            // 검색창에 필터 표시
            document.getElementById('search').value = `type:${type}`;
        }
        
        function renderGraph() {
            const container = document.getElementById('graph');
            
            Graph = ForceGraph3D()
                (container)
                .graphData(graphData)
                .nodeLabel(node => `<div style="background:rgba(0,0,0,0.8);padding:5px 10px;border-radius:4px;font-size:12px;">${node.name}</div>`)
                .nodeColor(node => TYPE_COLORS[node.type] || '#7f8c8d')
                .nodeVal(node => Math.max(3, (node.trust_score || 0.5) * 10))
                .linkColor(() => 'rgba(100, 100, 150, 0.3)')
                .linkWidth(0.5)
                .linkDirectionalArrowLength(3)
                .linkDirectionalArrowRelPos(1)
                .onNodeClick(node => {
                    const infoPanel = document.getElementById('info-panel');
                    const nodeInfo = document.getElementById('node-info');
                    
                    let propsHtml = '';
                    if (node.properties) {
                        const importantProps = ['price', 'market_cap', 'symbol', 'change_24h_percent'];
                        const props = Object.entries(node.properties)
                            .filter(([k, v]) => v !== null && v !== undefined && !k.startsWith('_'))
                            .slice(0, 10);
                        
                        propsHtml = props
                            .map(([k, v]) => {
                                let displayValue = v;
                                if (typeof v === 'number') {
                                    if (k.includes('price') || k.includes('cap')) {
                                        displayValue = '$' + v.toLocaleString();
                                    } else if (k.includes('percent')) {
                                        displayValue = v.toFixed(2) + '%';
                                    }
                                }
                                return `<span class="tag">${k}: ${displayValue}</span>`;
                            })
                            .join('');
                    }
                    
                    nodeInfo.innerHTML = `
                        <h4>${node.name}</h4>
                        <p><strong>Type:</strong> ${node.type}</p>
                        <p><strong>Trust Score:</strong> ${((node.trust_score || 0.5) * 100).toFixed(0)}%</p>
                        <p>${node.description || '설명 없음'}</p>
                        ${propsHtml ? `<div style="margin-top:8px;">${propsHtml}</div>` : ''}
                    `;
                    infoPanel.classList.add('active');
                    
                    // 카메라 이동
                    const distance = 100;
                    const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
                    Graph.cameraPosition(
                        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
                        node,
                        2000
                    );
                })
                .onBackgroundClick(() => {
                    closeInfoPanel();
                })
                .backgroundColor('#0a0a0f');
        }
        
        // 검색 기능
        document.getElementById('search').addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            if (!query) {
                Graph.graphData(graphData);
                return;
            }
            
            // type: 필터 지원
            if (query.startsWith('type:')) {
                const typeFilter = query.replace('type:', '').trim();
                const filteredNodes = graphData.nodes.filter(n => n.type === typeFilter);
                const nodeIds = new Set(filteredNodes.map(n => n.id));
                const filteredLinks = graphData.links.filter(l => 
                    nodeIds.has(l.source.id || l.source) && nodeIds.has(l.target.id || l.target)
                );
                Graph.graphData({ nodes: filteredNodes, links: filteredLinks });
                return;
            }
            
            const filteredNodes = graphData.nodes.filter(n => 
                n.name.toLowerCase().includes(query) || 
                (n.description && n.description.toLowerCase().includes(query)) ||
                n.type.toLowerCase().includes(query)
            );
            const nodeIds = new Set(filteredNodes.map(n => n.id));
            const filteredLinks = graphData.links.filter(l => 
                nodeIds.has(l.source.id || l.source) && nodeIds.has(l.target.id || l.target)
            );
            
            Graph.graphData({ nodes: filteredNodes, links: filteredLinks });
        });
        
        // 전체 데이터 다시 보기 (검색 초기화)
        document.getElementById('search').addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                e.target.value = '';
                Graph.graphData(graphData);
            }
        });
        
        // 화면 크기 변경 시 패널 상태 조정
        window.addEventListener('resize', () => {
            if (Graph) {
                Graph.width(window.innerWidth);
                Graph.height(window.innerHeight);
            }
        });
        
        // 이벤트 리스너 등록
        function setupEventListeners() {
            // 패널 헤더 클릭 이벤트
            document.getElementById('stats-header').addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                togglePanel('stats-panel');
            });
            
            document.getElementById('legend-header').addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                togglePanel('legend-panel');
            });
            
            // 정보 패널 닫기 버튼
            document.getElementById('info-close-btn').addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                closeInfoPanel();
            });
            
            // 모바일 토글 버튼
            document.getElementById('mobile-toggle-btn').addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                toggleAllPanels();
            });
            
            // 터치 이벤트 지원 (모바일)
            document.getElementById('stats-header').addEventListener('touchend', function(e) {
                e.preventDefault();
                togglePanel('stats-panel');
            });
            
            document.getElementById('legend-header').addEventListener('touchend', function(e) {
                e.preventDefault();
                togglePanel('legend-panel');
            });
        }
        
        // 초기화
        setupEventListeners();
        restorePanelStates();
        loadData();
    </script>
</body>
</html>
"""


@router.get("/viewer", response_class=HTMLResponse)
async def knowledge_graph_viewer():
    """지식 그래프 3D 시각화 페이지."""
    return VIEWER_HTML

