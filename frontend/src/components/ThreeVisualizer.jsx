import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'

export default function ThreeVisualizer() {
  const containerRef = useRef(null)
  const [isLowPower, setIsLowPower] = useState(false)
  const [webGlSupported, setWebGlSupported] = useState(true)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // 1. Accessibility Check: Prefers reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReducedMotion) {
      setIsLowPower(true)
    }

    // 2. WebGL Detection
    let renderer
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
      })
    } catch {
      setWebGlSupported(false)
      return
    }

    const width = container.clientWidth || 600
    const height = container.clientHeight || 500
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.15
    container.appendChild(renderer.domElement)

    // 3. Scene & Camera Setup
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100)
    camera.position.set(0, 1.2, 11)

    // 4. Lighting System
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2)
    scene.add(ambientLight)

    const keyLight = new THREE.DirectionalLight(0xe0f2fe, 2.4)
    keyLight.position.set(6, 8, 8)
    scene.add(keyLight)

    const fillLight = new THREE.DirectionalLight(0x38bdf8, 1.5)
    fillLight.position.set(-6, -2, 4)
    scene.add(fillLight)

    const bluePoint = new THREE.PointLight(0x2563eb, 3.5, 14)
    bluePoint.position.set(2, 0.5, 3)
    scene.add(bluePoint)

    const cyanPoint = new THREE.PointLight(0x06b6d4, 2.5, 12)
    cyanPoint.position.set(-3, -1, 2)
    scene.add(cyanPoint)

    // Visual Group for smooth global parallax
    const rootGroup = new THREE.Group()
    scene.add(rootGroup)

    // --- ELEMENT 1: 3D High-Res Canvas Dashboard Panel ---
    const canvas = document.createElement('canvas')
    canvas.width = 1024
    canvas.height = 640
    const ctx = canvas.getContext('2d')

    function drawDashboardTexture(t = 0) {
      if (!ctx) return
      // Background gradient
      const bgGrad = ctx.createLinearGradient(0, 0, 1024, 640)
      bgGrad.addColorStop(0, '#0f172a')
      bgGrad.addColorStop(0.5, '#0b1329')
      bgGrad.addColorStop(1, '#030712')
      ctx.fillStyle = bgGrad
      ctx.fillRect(0, 0, 1024, 640)

      // Outer Card Frame
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)'
      ctx.lineWidth = 3
      ctx.strokeRect(12, 12, 1000, 616)

      // Header Bar
      ctx.fillStyle = 'rgba(255, 255, 255, 0.05)'
      ctx.fillRect(12, 12, 1000, 80)

      // Brand Logo Pill
      ctx.fillStyle = '#2563eb'
      ctx.beginPath()
      ctx.roundRect(36, 26, 48, 48, 12)
      ctx.fill()
      ctx.fillStyle = '#ffffff'
      ctx.font = 'bold 24px Inter, sans-serif'
      ctx.fillText('S', 51, 60)

      // Brand Title
      ctx.fillStyle = '#ffffff'
      ctx.font = 'bold 22px Inter, sans-serif'
      ctx.fillText('SEPL AI RECONCILIATION SUITE', 100, 52)
      ctx.font = '13px Inter, sans-serif'
      ctx.fillStyle = '#38bdf8'
      ctx.fillText('SYNTHETIC BENCHMARK LEDGER • AUDITED', 100, 72)

      // Status Pill
      ctx.fillStyle = 'rgba(16, 185, 129, 0.2)'
      ctx.beginPath()
      ctx.roundRect(830, 32, 150, 36, 18)
      ctx.fill()
      ctx.strokeStyle = '#10b981'
      ctx.lineWidth = 1.5
      ctx.stroke()
      ctx.fillStyle = '#34d399'
      ctx.font = 'bold 13px Inter, sans-serif'
      ctx.fillText('● ZERO DELTA', 855, 55)

      // 3 KPI Cards
      const kpis = [
        { label: 'TOTAL INFLOW', val: '₹45,48,780.00', color: '#10b981', sub: '+12.4% Verified' },
        { label: 'TOTAL OUTFLOW', val: '₹46,26,410.00', color: '#f43f5e', sub: '99.98% Classified' },
        { label: 'NET VARIANCE', val: 'Δ = ₹0.00', color: '#38bdf8', sub: 'Perfect Balance' },
      ]

      kpis.forEach((kpi, idx) => {
        const x = 36 + idx * 324
        const y = 115
        ctx.fillStyle = 'rgba(30, 41, 59, 0.7)'
        ctx.beginPath()
        ctx.roundRect(x, y, 304, 110, 14)
        ctx.fill()
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)'
        ctx.stroke()

        ctx.fillStyle = '#94a3b8'
        ctx.font = '12px Inter, sans-serif'
        ctx.fillText(kpi.label, x + 20, y + 32)

        ctx.fillStyle = '#ffffff'
        ctx.font = 'bold 24px Inter, sans-serif'
        ctx.fillText(kpi.val, x + 20, y + 68)

        ctx.fillStyle = kpi.color
        ctx.font = '600 12px Inter, sans-serif'
        ctx.fillText(kpi.sub, x + 20, y + 94)
      })

      // Financial Cash-Flow Wave Graph
      ctx.fillStyle = 'rgba(30, 41, 59, 0.5)'
      ctx.beginPath()
      ctx.roundRect(36, 245, 952, 240, 14)
      ctx.fill()
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)'
      ctx.stroke()

      ctx.fillStyle = '#f8fafc'
      ctx.font = 'bold 15px Inter, sans-serif'
      ctx.fillText('Cash Flow Trajectory & Predictive Balance', 56, 280)
      ctx.fillStyle = '#64748b'
      ctx.font = '12px Inter, sans-serif'
      ctx.fillText('Synthetic Institutional Benchmark (Multi-Bank Structure • Daily Resolution)', 56, 300)

      // Grid lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)'
      ctx.lineWidth = 1
      for (let gy = 330; gy <= 450; gy += 40) {
        ctx.beginPath()
        ctx.moveTo(56, gy)
        ctx.lineTo(968, gy)
        ctx.stroke()
      }

      // Dynamic Spline Curve
      ctx.beginPath()
      const pts = [
        { x: 56, y: 420 },
        { x: 180, y: 390 + Math.sin(t * 1.5) * 8 },
        { x: 320, y: 360 + Math.cos(t * 1.2) * 10 },
        { x: 480, y: 410 + Math.sin(t * 2) * 6 },
        { x: 620, y: 340 + Math.sin(t * 1.4) * 12 },
        { x: 760, y: 370 + Math.cos(t * 1.8) * 8 },
        { x: 900, y: 330 + Math.sin(t * 1.6) * 10 },
        { x: 968, y: 350 },
      ]

      ctx.moveTo(pts[0].x, pts[0].y)
      for (let i = 1; i < pts.length; i++) {
        const xc = (pts[i].x + pts[i - 1].x) / 2
        const yc = (pts[i].y + pts[i - 1].y) / 2
        ctx.quadraticCurveTo(pts[i - 1].x, pts[i - 1].y, xc, yc)
      }
      ctx.strokeStyle = '#38bdf8'
      ctx.lineWidth = 3
      ctx.stroke()

      // Gradient fill under curve
      ctx.lineTo(968, 460)
      ctx.lineTo(56, 460)
      ctx.closePath()
      const areaGrad = ctx.createLinearGradient(0, 320, 0, 460)
      areaGrad.addColorStop(0, 'rgba(56, 189, 248, 0.25)')
      areaGrad.addColorStop(1, 'rgba(56, 189, 248, 0.0)')
      ctx.fillStyle = areaGrad
      ctx.fill()

      // Bottom Badges
      const badges = ['SOC 2 TYPE II COMPLIANT', '256-BIT TLS SESSION', 'ZERO RETENTION AI', '5 AUDIT DELIVERABLES']
      badges.forEach((b, i) => {
        const bx = 36 + i * 242
        ctx.fillStyle = 'rgba(15, 23, 42, 0.8)'
        ctx.beginPath()
        ctx.roundRect(bx, 510, 226, 44, 8)
        ctx.fill()
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.2)'
        ctx.stroke()
        ctx.fillStyle = '#94a3b8'
        ctx.font = 'bold 11px Inter, sans-serif'
        ctx.fillText('✓  ' + b, bx + 16, 536)
      })

      // Footer notice
      ctx.fillStyle = '#64748b'
      ctx.font = '11px Inter, sans-serif'
      ctx.fillText('SEPL Enterprise Platform • Powered by Smart Solutions Pvt Ltd', 36, 590)
    }

    drawDashboardTexture(0)
    const dashboardTexture = new THREE.CanvasTexture(canvas)
    dashboardTexture.minFilter = THREE.LinearFilter
    dashboardTexture.magFilter = THREE.LinearFilter

    // Dashboard Geometry & Material
    const panelGeo = new THREE.PlaneGeometry(6.4, 4.0)
    const panelMat = new THREE.MeshPhysicalMaterial({
      map: dashboardTexture,
      transparent: true,
      opacity: 0.98,
      roughness: 0.15,
      metalness: 0.1,
      clearcoat: 0.6,
      clearcoatRoughness: 0.1,
      side: THREE.DoubleSide,
    })
    const dashboardMesh = new THREE.Mesh(panelGeo, panelMat)
    dashboardMesh.position.set(0.6, 0.3, 0)
    dashboardMesh.rotation.y = -0.12
    dashboardMesh.rotation.x = 0.05
    rootGroup.add(dashboardMesh)

    // Glass panel back casing
    const casingGeo = new THREE.BoxGeometry(6.45, 4.05, 0.08)
    const casingMat = new THREE.MeshPhysicalMaterial({
      color: 0x0f172a,
      roughness: 0.2,
      metalness: 0.8,
      transparent: true,
      opacity: 0.85,
    })
    const casingMesh = new THREE.Mesh(casingGeo, casingMat)
    casingMesh.position.set(0.6, 0.3, -0.05)
    casingMesh.rotation.copy(dashboardMesh.rotation)
    rootGroup.add(casingMesh)

    // --- ELEMENT 2: 3D Stacked Database Cylinders (MongoDB Atlas Foundation) ---
    const dbGroup = new THREE.Group()
    dbGroup.position.set(-4.2, -1.8, 1.2)
    dbGroup.rotation.y = 0.35
    dbGroup.rotation.x = 0.2
    rootGroup.add(dbGroup)

    const cylinderGeo = new THREE.CylinderGeometry(1.2, 1.2, 0.32, 32)
    const dbMat = new THREE.MeshPhysicalMaterial({
      color: 0x1e3a8a,
      roughness: 0.25,
      metalness: 0.85,
      clearcoat: 0.5,
    })
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: false,
    })

    const dbRings = []
    for (let i = 0; i < 3; i++) {
      const disk = new THREE.Mesh(cylinderGeo, dbMat)
      disk.position.y = i * 0.45
      dbGroup.add(disk)

      // Glowing Cyan/Blue Status Ring
      const ringGeo = new THREE.TorusGeometry(1.23, 0.025, 12, 36)
      const ring = new THREE.Mesh(ringGeo, ringMat)
      ring.rotation.x = Math.PI / 2
      ring.position.y = i * 0.45
      dbGroup.add(ring)
      dbRings.push(ring)
    }

    // --- ELEMENT 3: 3D Animated Financial Bar Charts ---
    const barGroup = new THREE.Group()
    barGroup.position.set(4.3, -1.9, 0.8)
    barGroup.rotation.y = -0.3
    barGroup.rotation.x = 0.15
    rootGroup.add(barGroup)

    const bars = []
    const barHeights = [1.2, 2.1, 1.6, 2.7, 1.9, 3.2, 2.4]
    const barColors = [0x2563eb, 0x0284c7, 0x10b981, 0x38bdf8, 0x6366f1, 0x059669, 0x1d4ed8]

    for (let i = 0; i < 7; i++) {
      const bGeo = new THREE.BoxGeometry(0.38, 1, 0.38)
      const bMat = new THREE.MeshPhysicalMaterial({
        color: barColors[i],
        roughness: 0.2,
        metalness: 0.5,
        clearcoat: 0.4,
      })
      const bar = new THREE.Mesh(bGeo, bMat)
      bar.position.set((i - 3) * 0.55, barHeights[i] / 2, 0)
      bar.scale.y = barHeights[i]
      barGroup.add(bar)
      bars.push({ mesh: bar, baseHeight: barHeights[i], speed: 1.2 + i * 0.2, phase: i * 0.8 })
    }

    // Chart Base Platform
    const platformGeo = new THREE.BoxGeometry(4.2, 0.12, 1.2)
    const platformMat = new THREE.MeshPhysicalMaterial({
      color: 0x0f172a,
      roughness: 0.3,
      metalness: 0.7,
    })
    const platform = new THREE.Mesh(platformGeo, platformMat)
    platform.position.set(0, -0.06, 0)
    barGroup.add(platform)

    // --- ELEMENT 4: Curved Glowing Data Stream Pathways ---
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-4.0, -1.0, 1.0),
      new THREE.Vector3(-2.0, 0.2, 2.2),
      new THREE.Vector3(0.0, -0.2, 1.5),
      new THREE.Vector3(2.5, 0.6, 2.0),
      new THREE.Vector3(4.0, -0.5, 0.9),
    ])

    const tubeGeo = new THREE.TubeGeometry(curve, 64, 0.025, 8, false)
    const tubeMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.45,
    })
    const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat)
    rootGroup.add(tubeMesh)

    // Data Packets (Glowing traveling particles)
    const packetCount = 8
    const packetGeo = new THREE.SphereGeometry(0.09, 16, 16)
    const packetMat = new THREE.MeshBasicMaterial({ color: 0x67e8f9 })
    const packets = []

    for (let i = 0; i < packetCount; i++) {
      const pMesh = new THREE.Mesh(packetGeo, packetMat)
      rootGroup.add(pMesh)
      packets.push({ mesh: pMesh, progress: i / packetCount, speed: 0.18 })
    }

    // --- ELEMENT 5: Floating AI Neural Diamond Hologram ---
    const diamondGeo = new THREE.OctahedronGeometry(0.55, 0)
    const diamondMat = new THREE.MeshPhysicalMaterial({
      color: 0x38bdf8,
      wireframe: true,
      roughness: 0.1,
      metalness: 0.9,
      emissive: 0x1d4ed8,
      emissiveIntensity: 0.8,
    })
    const diamondMesh = new THREE.Mesh(diamondGeo, diamondMat)
    diamondMesh.position.set(-2.8, 2.2, 1.5)
    rootGroup.add(diamondMesh)

    // Inner glowing core
    const coreGeo = new THREE.SphereGeometry(0.2, 16, 16)
    const coreMat = new THREE.MeshBasicMaterial({ color: 0x60a5fa })
    const coreMesh = new THREE.Mesh(coreGeo, coreMat)
    coreMesh.position.copy(diamondMesh.position)
    rootGroup.add(coreMesh)

    // Floating Ring around Diamond
    const neuralRingGeo = new THREE.TorusGeometry(0.85, 0.02, 16, 48)
    const neuralRingMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4 })
    const neuralRing = new THREE.Mesh(neuralRingGeo, neuralRingMat)
    neuralRing.position.copy(diamondMesh.position)
    rootGroup.add(neuralRing)

    // --- ELEMENT 6: Background Ambient Floating Financial Particles ---
    const particleCount = 120
    const partGeo = new THREE.BufferGeometry()
    const partPositions = new Float32Array(particleCount * 3)

    for (let i = 0; i < particleCount * 3; i += 3) {
      partPositions[i] = (Math.random() - 0.5) * 22
      partPositions[i + 1] = (Math.random() - 0.5) * 14
      partPositions[i + 2] = (Math.random() - 0.5) * 12 - 2
    }
    partGeo.setAttribute('position', new THREE.BufferAttribute(partPositions, 3))

    const partMat = new THREE.PointsMaterial({
      color: 0x93c5fd,
      size: 0.08,
      transparent: true,
      opacity: 0.6,
    })
    const particleSystem = new THREE.Points(partGeo, partMat)
    scene.add(particleSystem)

    // --- Interaction & Mouse Parallax ---
    let mouseX = 0
    let mouseY = 0
    let targetX = 0
    let targetY = 0

    function onMouseMove(e) {
      const rect = container.getBoundingClientRect()
      mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1
      mouseY = -(((e.clientY - rect.top) / rect.height) * 2 - 1)
    }
    window.addEventListener('mousemove', onMouseMove)

    // Responsive Resize Handler
    function handleResize() {
      if (!container) return
      const w = container.clientWidth || 600
      const h = container.clientHeight || 500
      camera.aspect = w / h

      // Mobile camera framing adjustment
      if (w < 640) {
        camera.position.z = 15.5
        camera.position.y = 1.0
      } else if (w < 1024) {
        camera.position.z = 13.0
        camera.position.y = 1.1
      } else {
        camera.position.z = 11.0
        camera.position.y = 1.2
      }

      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }

    const resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(container)
    handleResize()

    // --- Animation Loop ---
    let clock = new THREE.Clock()
    let animId = null
    let textureUpdateTimer = 0

    function animate() {
      animId = requestAnimationFrame(animate)
      const delta = clock.getDelta()
      const time = clock.getElapsedTime()

      // Mouse Parallax Easing
      targetX += (mouseX * 0.35 - targetX) * 0.05
      targetY += (mouseY * 0.25 - targetY) * 0.05
      rootGroup.rotation.y = targetX
      rootGroup.rotation.x = -targetY

      // Dashboard gentle floating bob
      dashboardMesh.position.y = 0.3 + Math.sin(time * 1.1) * 0.14
      casingMesh.position.y = dashboardMesh.position.y
      dashboardMesh.rotation.z = Math.sin(time * 0.7) * 0.015
      casingMesh.rotation.z = dashboardMesh.rotation.z

      // Update 2D Canvas chart on the 3D surface every ~60ms
      textureUpdateTimer += delta
      if (textureUpdateTimer > 0.06) {
        textureUpdateTimer = 0
        drawDashboardTexture(time)
        dashboardTexture.needsUpdate = true
      }

      // Bar Chart dynamic heights
      bars.forEach((b) => {
        const h = b.baseHeight + Math.sin(time * b.speed + b.phase) * 0.35
        b.mesh.scale.y = Math.max(0.2, h)
        b.mesh.position.y = h / 2
      })

      // Database Ring Pulses
      dbRings.forEach((r, idx) => {
        const s = 1 + Math.sin(time * 3 + idx * 1.5) * 0.04
        r.scale.set(s, s, s)
      })
      dbGroup.rotation.y = 0.35 + Math.sin(time * 0.8) * 0.08

      // Traveling Data Packets along the Catmull curve
      packets.forEach((p) => {
        p.progress += p.speed * delta
        if (p.progress > 1) p.progress -= 1
        const pt = curve.getPoint(p.progress)
        p.mesh.position.copy(pt)
      })

      // Hologram Diamond Rotation
      diamondMesh.rotation.x += 0.8 * delta
      diamondMesh.rotation.y += 1.1 * delta
      neuralRing.rotation.z += 1.4 * delta
      neuralRing.rotation.x = Math.sin(time) * 0.4
      coreMesh.scale.setScalar(1 + Math.sin(time * 4) * 0.15)

      // Background particle drift
      particleSystem.rotation.y = time * 0.02

      renderer.render(scene, camera)
    }

    if (!prefersReducedMotion) {
      animate()
    } else {
      // Single frame render for reduced motion
      drawDashboardTexture(0)
      dashboardTexture.needsUpdate = true
      renderer.render(scene, camera)
    }

    // Cleanup on unmount
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      resizeObserver.disconnect()
      if (animId) cancelAnimationFrame(animId)
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
      renderer.dispose()
      panelGeo.dispose()
      panelMat.dispose()
      casingGeo.dispose()
      casingMat.dispose()
      cylinderGeo.dispose()
      dbMat.dispose()
      ringMat.dispose()
      tubeGeo.dispose()
      tubeMat.dispose()
      packetGeo.dispose()
      packetMat.dispose()
      diamondGeo.dispose()
      diamondMat.dispose()
      coreGeo.dispose()
      coreMat.dispose()
      neuralRingGeo.dispose()
      neuralRingMat.dispose()
      partGeo.dispose()
      partMat.dispose()
      dashboardTexture.dispose()
    }
  }, [])

  return (
    <div
      ref={containerRef}
      className="relative w-full h-[480px] sm:h-[540px] md:h-[600px] lg:h-[660px] flex items-center justify-center select-none overflow-hidden"
      role="img"
      aria-label="3D Financial Analytics and Data Reconciliation Visualization"
    >
      {!webGlSupported && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/90 text-white p-6 rounded-2xl text-center">
          <div className="text-3xl mb-2">📊</div>
          <p className="font-semibold text-lg">SEPL Financial Intelligence Hub</p>
          <p className="text-sm text-slate-400 mt-1">WebGL is disabled or unsupported on this display device.</p>
        </div>
      )}

      {isLowPower && (
        <div className="absolute bottom-3 left-4 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full text-[11px] text-cyan-300 border border-cyan-500/30">
          Reduced Motion Active
        </div>
      )}
    </div>
  )
}
