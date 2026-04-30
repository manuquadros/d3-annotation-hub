<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:jats="https://jats.nlm.nih.gov/ns/archiving/1.3/" xmlns:xlink="http://www.w3.org/1999/xlink" version="2.0" exclude-result-prefixes="jats xlink">
  <!-- Output HTML -->
  <xsl:output method="html" encoding="UTF-8" indent="yes"/>
  <!-- Template for the root element (body) -->
  <xsl:template match="/jats:body">
    <div class="jats-body">
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <!-- sec → section -->
  <xsl:template match="*[local-name()='sec']">
    <section>
      <xsl:for-each select="@*">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
      </xsl:for-each>
      <xsl:apply-templates/>
    </section>
  </xsl:template>

  <!-- title inside sec → depth-based heading (h2–h6) -->
  <xsl:template match="*[local-name()='sec']/*[local-name()='title']">
    <xsl:variable name="depth" select="count(ancestor::*[local-name()='sec'])"/>
    <xsl:variable name="level">
      <xsl:choose>
        <xsl:when test="$depth &gt;= 5">h6</xsl:when>
        <xsl:when test="$depth = 4">h5</xsl:when>
        <xsl:when test="$depth = 3">h4</xsl:when>
        <xsl:when test="$depth = 2">h3</xsl:when>
        <xsl:otherwise>h2</xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:element name="{$level}">
      <xsl:apply-templates/>
    </xsl:element>
  </xsl:template>

  <!-- xref → a -->
  <xsl:template match="*[local-name()='xref']">
    <a>
      <xsl:if test="@rid">
        <xsl:attribute name="href">#<xsl:value-of select="@rid"/></xsl:attribute>
      </xsl:if>
      <xsl:apply-templates/>
    </a>
  </xsl:template>

  <!-- ext-link → a -->
  <xsl:template match="*[local-name()='ext-link']">
    <a>
      <xsl:if test="@xlink:href">
        <xsl:attribute name="href">
          <xsl:value-of select="@xlink:href"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:apply-templates/>
    </a>
  </xsl:template>

  <!-- italic → em -->
  <xsl:template match="*[local-name()='italic']">
    <em><xsl:apply-templates/></em>
  </xsl:template>

  <!-- bold → strong -->
  <xsl:template match="*[local-name()='bold']">
    <strong><xsl:apply-templates/></strong>
  </xsl:template>

  <!-- sc → span.sc (small caps via CSS) -->
  <xsl:template match="*[local-name()='sc']">
    <span class="sc"><xsl:apply-templates/></span>
  </xsl:template>

  <!-- Generic template to remove namespace but keep tag names and attributes -->
  <xsl:template match="*">
    <xsl:element name="{local-name()}">
      <xsl:for-each select="@*">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
      </xsl:for-each>
      <xsl:apply-templates/>
    </xsl:element>
  </xsl:template>
</xsl:stylesheet>
